from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from drf_spectacular.utils import extend_schema, OpenApiExample

from .models import CreditTransaction, UserCredit
from .serializers import (
    CreditTransactionSerializer, CreditBalanceSerializer,
    CreditAdjustmentSerializer, UserClassInfoSerializer
)
from accounts.models import User
from logging_monitoring.models import SystemLog, Alert


@extend_schema(
    tags=['Credit System'],
    summary='User Credit Balance',
    description='Get the current credit balance and statistics for the authenticated user.',
    responses={
        200: OpenApiExample(
            'Credit Balance',
            value={
                'total_credit': '50.00',
                'locked_credit': '5.00',
                'available_credit': '45.00',
                'lifetime_earned': '150.00',
                'lifetime_spent': '100.00'
            }
        )
    }
)
class CreditBalanceView(generics.RetrieveAPIView):
    """Get user's credit balance and statistics"""

    serializer_class = CreditBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        return {
            'total_credit': user.total_credit,
            'locked_credit': user.locked_credit,
            'available_credit': user.available_credit,
            'lifetime_upload': user.lifetime_upload,
            'lifetime_download': user.lifetime_download,
            'ratio': user.ratio,
            'user_class': user.user_class,
            'download_multiplier': user.download_multiplier,
            'max_torrents': user.max_torrents,
        }


class CreditTransactionListView(generics.ListAPIView):
    """نمای لیست تراکنش‌های credit"""

    serializer_class = CreditTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    paginate_by = 20

    def get_queryset(self):
        return CreditTransaction.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class CreditTransactionDetailView(generics.RetrieveAPIView):
    """نمای جزئیات تراکنش credit"""

    serializer_class = CreditTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CreditTransaction.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_class_info(request):
    """نمایش اطلاعات کلاس‌های کاربری"""

    user_classes = {
        'newbie': {
            'requirements': {
                'min_ratio': 0,
                'min_upload': 0,
                'account_age_days': 0,
            },
            'benefits': {
                'download_multiplier': 0.5,
                'bonus_points': 1.0,
            },
            'restrictions': {
                'max_torrents': 1,
                'max_download_speed': 'unlimited',
            }
        },
        'member': {
            'requirements': {
                'min_ratio': 0.5,
                'min_upload': 10 * 1024 * 1024 * 1024,  # 10 GB
                'account_age_days': 7,
            },
            'benefits': {
                'download_multiplier': 1.0,
                'bonus_points': 1.0,
            },
            'restrictions': {
                'max_torrents': 5,
                'max_download_speed': 'unlimited',
            }
        },
        'trusted': {
            'requirements': {
                'min_ratio': 1.0,
                'min_upload': 100 * 1024 * 1024 * 1024,  # 100 GB
                'account_age_days': 30,
            },
            'benefits': {
                'download_multiplier': 1.5,
                'bonus_points': 1.5,
            },
            'restrictions': {
                'max_torrents': 15,
                'max_download_speed': 'unlimited',
            }
        },
        'elite': {
            'requirements': {
                'min_ratio': 2.0,
                'min_upload': 500 * 1024 * 1024 * 1024,  # 500 GB
                'account_age_days': 90,
            },
            'benefits': {
                'download_multiplier': 2.0,
                'bonus_points': 2.0,
            },
            'restrictions': {
                'max_torrents': 50,
                'max_download_speed': 'unlimited',
            }
        },
    }

    return Response(user_classes)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_download_permission(request):
    """بررسی امکان دانلود تورنت"""

    try:
        torrent_size_gb = request.data.get('torrent_size_gb', 0)
        if not torrent_size_gb:
            return Response(
                {'error': 'torrent_size_gb is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        required_credit = Decimal(str(torrent_size_gb))

        # بررسی credit کافی
        if user.available_credit < required_credit:
            return Response({
                'can_download': False,
                'reason': 'insufficient_credit',
                'required_credit': required_credit,
                'available_credit': user.available_credit,
                'shortage': required_credit - user.available_credit
            })

        # بررسی محدودیت تورنت
        active_torrents = user.peers.filter(state__in=['started', 'completed']).count()
        if active_torrents >= user.max_torrents:
            return Response({
                'can_download': False,
                'reason': 'max_torrents_reached',
                'current_torrents': active_torrents,
                'max_torrents': user.max_torrents
            })

        # بررسی ratio
        if user.ratio < 0.1 and user.lifetime_download > 1024 * 1024 * 1024:  # 1 GB
            return Response({
                'can_download': False,
                'reason': 'low_ratio',
                'current_ratio': user.ratio,
                'min_ratio': 0.1
            })

        return Response({
            'can_download': True,
            'required_credit': required_credit,
            'available_credit': user.available_credit,
            'user_class': user.user_class,
            'download_multiplier': user.download_multiplier
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def lock_credit_for_download(request):
    """قفل کردن credit برای دانلود"""

    try:
        torrent_id = request.data.get('torrent_id')

        if not torrent_id:
            return Response(
                {'error': 'torrent_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get torrent and calculate required credits
        try:
            from torrents.models import Torrent
            torrent = Torrent.objects.get(id=torrent_id, is_active=True)
        except Torrent.DoesNotExist:
            return Response(
                {'error': 'Torrent not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check access permissions for private torrents
        if torrent.is_private and torrent.created_by != request.user:
            return Response(
                {'error': 'Access denied to private torrent'},
                status=status.HTTP_403_FORBIDDEN
            )

        user = request.user
        torrent_size_gb = torrent.size / (1024 ** 3)
        required_credit = Decimal(str(torrent_size_gb))

        with transaction.atomic():
            # بررسی مجدد اعتبار
            if user.available_credit < required_credit:
                return Response(
                    {'error': 'Insufficient credit'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # قفل کردن credit
            user.locked_credit += required_credit
            user.save(update_fields=['locked_credit'])

            # ایجاد تراکنش pending
            transaction_obj = CreditTransaction.objects.create(
                user=user,
                torrent_id=torrent_id,
                transaction_type='download',
                amount=required_credit,
                description=f'Locked credit for download (Torrent ID: {torrent_id})',
                status='pending'
            )

            return Response({
                'success': True,
                'transaction_id': transaction_obj.id,
                'locked_credit': required_credit,
                'remaining_credit': user.available_credit - required_credit
            })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def complete_download_transaction(request):
    """تکمیل تراکنش دانلود"""

    try:
        transaction_id = request.data.get('transaction_id')
        actual_downloaded_bytes = request.data.get('downloaded_bytes', 0)

        if not transaction_id:
            return Response(
                {'error': 'transaction_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        with transaction.atomic():
            # یافتن تراکنش
            try:
                transaction_obj = CreditTransaction.objects.get(
                    id=transaction_id,
                    user=user,
                    transaction_type='download',
                    status='pending'
                )
            except CreditTransaction.DoesNotExist:
                return Response(
                    {'error': 'Transaction not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # محاسبه credit واقعی بر اساس دانلود
            actual_downloaded_gb = actual_downloaded_bytes / (1024 ** 3)
            final_credit = Decimal(str(actual_downloaded_gb))

            # بروزرسانی تراکنش
            transaction_obj.amount = final_credit
            transaction_obj.status = 'completed'
            transaction_obj.processed_at = timezone.now()
            transaction_obj.description += f' - Completed: {actual_downloaded_gb:.2f} GB'
            transaction_obj.save()

            # آزاد کردن credit اضافی
            credit_difference = transaction_obj.amount - final_credit
            if credit_difference > 0:
                user.locked_credit -= credit_difference
                user.save(update_fields=['locked_credit'])

            return Response({
                'success': True,
                'final_credit_used': final_credit,
                'credit_returned': credit_difference if credit_difference > 0 else 0
            })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_upload_credit(request):
    """محاسبه credit آپلود"""

    try:
        uploaded_bytes = request.data.get('uploaded_bytes', 0)
        torrent_id = request.data.get('torrent_id')

        if not uploaded_bytes or not torrent_id:
            return Response(
                {'error': 'uploaded_bytes and torrent_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        # محاسبه credit
        uploaded_gb = uploaded_bytes / (1024 ** 3)
        credit_amount = Decimal(str(uploaded_gb)) * Decimal(str(settings.BITTORRENT_SETTINGS['CREDIT_MULTIPLIER']))

        # اعمال ضریب کاربر
        credit_amount *= Decimal(str(user.download_multiplier))

        with transaction.atomic():
            # ایجاد تراکنش credit
            CreditTransaction.objects.create(
                user=user,
                torrent_id=torrent_id,
                transaction_type='upload',
                amount=credit_amount,
                description=f'Upload credit: {uploaded_gb:.2f} GB'
            )

            return Response({
                'credit_earned': credit_amount,
                'uploaded_gb': uploaded_gb,
                'multiplier': user.download_multiplier
            })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_ratio_status(request):
    """بررسی وضعیت ratio کاربر"""

    user = request.user

    ratio_status = {
        'current_ratio': user.ratio,
        'lifetime_upload': user.lifetime_upload,
        'lifetime_download': user.lifetime_download,
        'status': 'good'
    }

    # بررسی هشدارها
    if user.ratio < 0.5 and user.lifetime_download > 1024 * 1024 * 1024:  # 1 GB
        ratio_status['status'] = 'warning'
        ratio_status['message'] = 'Ratio is below 0.5. Consider uploading more.'
    elif user.ratio < 0.1:
        ratio_status['status'] = 'critical'
        ratio_status['message'] = 'Ratio is critically low. Upload immediately to avoid restrictions.'

        # ایجاد alert
        Alert.objects.create(
            alert_type='ratio_anomaly',
            priority='high',
            title='Critical Ratio Warning',
            message=f'User {user.username} has critically low ratio: {user.ratio:.3f}',
            user=user,
            details={'ratio': user.ratio, 'upload': user.lifetime_upload, 'download': user.lifetime_download}
        )

    return Response(ratio_status)


# Admin functions
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def adjust_user_credit(request):
    """تنظیم credit کاربر توسط ادمین"""

    serializer = CreditAdjustmentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=serializer.validated_data['user_id'])
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    amount = serializer.validated_data['amount']
    reason = serializer.validated_data['reason']
    transaction_type = serializer.validated_data['transaction_type']

    try:
        with transaction.atomic():
            # ایجاد تراکنش
            CreditTransaction.objects.create(
                user=user,
                transaction_type=transaction_type,
                amount=amount,
                description=f'Admin adjustment: {reason}'
            )

            # لاگ سیستم
            SystemLog.objects.create(
                category='admin',
                level='info',
                message=f'Admin {request.user.username} adjusted credit for {user.username}: {amount}',
                details={
                    'admin_id': request.user.id,
                    'user_id': user.id,
                    'amount': str(amount),
                    'reason': reason
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user=request.user
            )

            return Response({
                'success': True,
                'user': user.username,
                'adjustment': amount,
                'new_balance': user.available_credit
            })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def promote_user_class(request):
    """ارتقا کلاس کاربر"""

    try:
        user_id = request.data.get('user_id')
        new_class = request.data.get('new_class')

        if not user_id or not new_class:
            return Response(
                {'error': 'user_id and new_class are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.get(id=user_id)

        # بررسی امکان ارتقا
        if not can_promote_user(user, new_class):
            return Response(
                {'error': 'User does not meet requirements for this class'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_class = user.user_class
        user.user_class = new_class
        user.save(update_fields=['user_class'])

        # لاگ ارتقا
        SystemLog.objects.create(
            category='admin',
            level='info',
            message=f'User {user.username} promoted from {old_class} to {new_class}',
            details={
                'admin_id': request.user.id,
                'user_id': user.id,
                'old_class': old_class,
                'new_class': new_class
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user=request.user
        )

        return Response({
            'success': True,
            'user': user.username,
            'old_class': old_class,
            'new_class': new_class
        })

    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def can_promote_user(user, target_class):
    """بررسی امکان ارتقا کاربر"""

    requirements = {
        'member': {
            'min_ratio': 0.5,
            'min_upload': 10 * 1024 * 1024 * 1024,  # 10 GB
            'account_age_days': 7,
        },
        'trusted': {
            'min_ratio': 1.0,
            'min_upload': 100 * 1024 * 1024 * 1024,  # 100 GB
            'account_age_days': 30,
        },
        'elite': {
            'min_ratio': 2.0,
            'min_upload': 500 * 1024 * 1024 * 1024,  # 500 GB
            'account_age_days': 90,
        },
    }

    if target_class not in requirements:
        return False

    req = requirements[target_class]

    # بررسی ratio
    if user.ratio < req['min_ratio']:
        return False

    # بررسی آپلود
    if user.lifetime_upload < req['min_upload']:
        return False

    # بررسی سن حساب
    from django.utils import timezone
    account_age = (timezone.now() - user.date_joined).days
    if account_age < req['account_age_days']:
        return False

    return True