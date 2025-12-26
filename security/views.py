from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from .models import SuspiciousActivity, AnnounceLog, IPBlock, RateLimit
from .serializers import (
    SuspiciousActivitySerializer, AnnounceLogSerializer,
    IPBlockSerializer, SecurityStatsSerializer, SecurityReportSerializer
)
from logging_monitoring.models import SystemLog, Alert
from accounts.models import User


class SuspiciousActivityListView(generics.ListAPIView):
    """نمای لیست فعالیت‌های مشکوک"""

    serializer_class = SuspiciousActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    paginate_by = 20

    def get_queryset(self):
        queryset = SuspiciousActivity.objects.all()

        # فیلترها
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        activity_type = self.request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)

        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)

        resolved = self.request.query_params.get('resolved')
        if resolved is not None:
            queryset = queryset.filter(is_resolved=resolved.lower() == 'true')

        return queryset.order_by('-detected_at')


class SuspiciousActivityDetailView(generics.RetrieveUpdateAPIView):
    """نمای جزئیات فعالیت مشکوک"""

    serializer_class = SuspiciousActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SuspiciousActivity.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        resolved = request.data.get('is_resolved', False)

        if resolved and not instance.is_resolved:
            instance.is_resolved = True
            instance.resolved_at = timezone.now()
            instance.resolved_by = request.user
            instance.save()

            # لاگ resolve
            SystemLog.objects.create(
                category='security',
                level='info',
                message=f'Suspicious activity resolved by {request.user.username}',
                details={
                    'activity_id': instance.id,
                    'activity_type': instance.activity_type,
                    'user_id': instance.user.id if instance.user else None
                },
                user=request.user
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class AnnounceLogListView(generics.ListAPIView):
    """نمای لیست لاگ announce"""

    serializer_class = AnnounceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    paginate_by = 50

    def get_queryset(self):
        queryset = AnnounceLog.objects.all()

        # فیلترها
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        torrent_id = self.request.query_params.get('torrent_id')
        if torrent_id:
            queryset = queryset.filter(torrent_id=torrent_id)

        ip_address = self.request.query_params.get('ip_address')
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)

        suspicious = self.request.query_params.get('suspicious')
        if suspicious is not None:
            queryset = queryset.filter(is_suspicious=suspicious.lower() == 'true')

        return queryset.order_by('-timestamp')


class IPBlockListView(generics.ListCreateAPIView):
    """نمای لیست و ایجاد مسدودی IP"""

    serializer_class = IPBlockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return IPBlock.objects.filter(is_active=True).order_by('-blocked_at')

    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = serializer.validated_data['ip_address']

        # بررسی وجود مسدودی قبلی
        existing_block = IPBlock.objects.filter(
            ip_address=ip_address,
            is_active=True
        ).first()

        if existing_block:
            return Response(
                {'error': 'IP is already blocked'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ایجاد مسدودی
        instance = serializer.save(blocked_by=request.user)

        # لاگ مسدودی
        SystemLog.objects.create(
            category='security',
            level='warning',
            message=f'IP blocked: {ip_address}',
            details={
                'ip_address': ip_address,
                'reason': instance.reason,
                'expires_at': str(instance.expires_at) if instance.expires_at else None
            },
            user=request.user
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class IPBlockDetailView(generics.RetrieveUpdateDestroyAPIView):
    """نمای جزئیات مسدودی IP"""

    serializer_class = IPBlockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return IPBlock.objects.all()

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        instance = self.get_object()
        instance.is_active = False
        instance.save()

        # لاگ رفع مسدودی
        SystemLog.objects.create(
            category='security',
            level='info',
            message=f'IP unblocked: {instance.ip_address}',
            details={'ip_address': instance.ip_address},
            user=request.user
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def security_stats(request):
    """آمار امنیتی"""

    # آمار فعالیت‌های مشکوک
    suspicious_count = SuspiciousActivity.objects.filter(
        detected_at__gte=timezone.now() - timedelta(days=30)
    ).count()

    # IP های مسدود فعال
    active_blocks = IPBlock.objects.filter(is_active=True).count()

    # بن‌های اخیر (کاربران مسدود شده)
    recent_bans = User.objects.filter(
        is_banned=True,
        banned_at__gte=timezone.now() - timedelta(days=7)
    ).count()

    # IP های مشکوک برتر
    top_suspicious_ips = list(
        SuspiciousActivity.objects.filter(
            detected_at__gte=timezone.now() - timedelta(days=30)
        ).values('ip_address').annotate(
            count=Count('ip_address')
        ).order_by('-count')[:10]
    )

    # هشدارهای امنیتی امروز
    today_alerts = Alert.objects.filter(
        alert_type__in=['ratio_anomaly', 'security_breach'],
        created_at__date=timezone.now().date()
    ).count()

    data = {
        'total_suspicious_activities': suspicious_count,
        'active_ip_blocks': active_blocks,
        'recent_bans': recent_bans,
        'top_suspicious_ips': top_suspicious_ips,
        'security_alerts_today': today_alerts,
    }

    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_user_behavior(request):
    """تحلیل رفتار کاربر"""

    user_id = request.data.get('user_id')
    days = int(request.data.get('days', 7))

    if not user_id:
        return Response(
            {'error': 'user_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # تحلیل announce logs
    start_date = timezone.now() - timedelta(days=days)
    announce_logs = AnnounceLog.objects.filter(
        user=user,
        timestamp__gte=start_date
    )

    # آمار پایه
    total_announces = announce_logs.count()
    suspicious_announces = announce_logs.filter(is_suspicious=True).count()

    # الگوی announce
    announces_per_day = announce_logs.extra(
        select={'day': "DATE(timestamp)"}
    ).values('day').annotate(count=Count('id')).order_by('day')

    # فعالیت‌های مشکوک
    suspicious_activities = SuspiciousActivity.objects.filter(
        user=user,
        detected_at__gte=start_date
    ).values('activity_type').annotate(count=Count('activity_type'))

    # تحلیل ratio
    ratio_trend = []
    current_date = start_date
    while current_date <= timezone.now():
        day_logs = announce_logs.filter(
            timestamp__date=current_date.date()
        )
        if day_logs.exists():
            upload_sum = sum(log.uploaded for log in day_logs)
            download_sum = sum(log.downloaded for log in day_logs)
            ratio = upload_sum / download_sum if download_sum > 0 else float('inf')
            ratio_trend.append({
                'date': current_date.date(),
                'ratio': min(ratio, 999.99)
            })
        current_date += timedelta(days=1)

    analysis = {
        'user_id': user.id,
        'username': user.username,
        'analysis_period_days': days,
        'total_announces': total_announces,
        'suspicious_announces': suspicious_announces,
        'suspicious_percentage': (suspicious_announces / total_announces * 100) if total_announces > 0 else 0,
        'announces_per_day': list(announces_per_day),
        'suspicious_activities': list(suspicious_activities),
        'ratio_trend': ratio_trend,
        'recommendations': generate_security_recommendations(user, announce_logs, suspicious_activities)
    }

    return Response(analysis)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ban_user(request):
    """مسدود کردن کاربر"""

    if not request.user.is_staff:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    user_id = request.data.get('user_id')
    reason = request.data.get('reason', 'Administrative ban')
    ban_duration_days = request.data.get('ban_duration_days')

    if not user_id:
        return Response(
            {'error': 'user_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if user.is_banned:
        return Response(
            {'error': 'User is already banned'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # مسدود کردن کاربر
    user.is_banned = True
    user.ban_reason = reason
    user.banned_at = timezone.now()
    user.save(update_fields=['is_banned', 'ban_reason', 'banned_at'])

    # باطل کردن توکن‌ها
    from accounts.models import AuthToken
    AuthToken.objects.filter(user=user).update(is_active=False)

    # ایجاد فعالیت مشکوک
    SuspiciousActivity.objects.create(
        user=user,
        activity_type='account_ban',
        severity='critical',
        description=f'User banned: {reason}',
        details={'banned_by': request.user.username, 'reason': reason},
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # لاگ سیستم
    SystemLog.objects.create(
        category='security',
        level='warning',
        message=f'User banned: {user.username}',
        details={
            'user_id': user.id,
            'reason': reason,
            'banned_by': request.user.username
        },
        user=request.user
    )

    return Response({
        'success': True,
        'message': f'User {user.username} has been banned',
        'ban_reason': reason
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unban_user(request):
    """رفع مسدودی کاربر"""

    if not request.user.is_staff:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    user_id = request.data.get('user_id')

    if not user_id:
        return Response(
            {'error': 'user_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if not user.is_banned:
        return Response(
            {'error': 'User is not banned'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # رفع مسدودی
    user.is_banned = False
    user.ban_reason = ''
    user.banned_at = None
    user.save(update_fields=['is_banned', 'ban_reason', 'banned_at'])

    # لاگ سیستم
    SystemLog.objects.create(
        category='security',
        level='info',
        message=f'User unbanned: {user.username}',
        details={
            'user_id': user.id,
            'unbanned_by': request.user.username
        },
        user=request.user
    )

    return Response({
        'success': True,
        'message': f'User {user.username} has been unbanned'
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def clear_rate_limits(request):
    """پاکسازی محدودیت‌های نرخ"""

    if not request.user.is_staff:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    identifier = request.data.get('identifier')
    limit_type = request.data.get('limit_type')

    # پاکسازی از cache
    if identifier and limit_type:
        cache_key = f"ratelimit:{limit_type}:{identifier}"
        cache.delete(cache_key)

        # پاکسازی از database
        RateLimit.objects.filter(
            identifier=identifier,
            limit_type=limit_type
        ).delete()

        message = f"Cleared rate limits for {identifier}:{limit_type}"
    else:
        # پاکسازی همه
        cache.delete_pattern("ratelimit:*")
        RateLimit.objects.all().delete()
        message = "Cleared all rate limits"

    return Response({'success': True, 'message': message})


def generate_security_recommendations(user, announce_logs, suspicious_activities):
    """تولید توصیه‌های امنیتی"""

    recommendations = []

    # بررسی تعداد announce های مشکوک
    suspicious_count = sum(activity['count'] for activity in suspicious_activities)
    if suspicious_count > 10:
        recommendations.append("High number of suspicious activities detected")

    # بررسی الگوی announce
    total_announces = announce_logs.count()
    if total_announces > 1000:  # بیش از ۱۰۰۰ announce در هفته
        recommendations.append("Excessive announce frequency detected")

    # بررسی ratio
    if user.ratio < 0.1:
        recommendations.append("Critically low ratio - consider temporary ban")
    elif user.ratio < 0.5:
        recommendations.append("Low ratio - monitor closely")

    # بررسی فعالیت‌های مشکوک خاص
    activity_types = [activity['activity_type'] for activity in suspicious_activities]
    if 'fake_upload' in activity_types:
        recommendations.append("Fake upload attempts detected")
    if 'abnormal_ratio' in activity_types:
        recommendations.append("Abnormal ratio patterns detected")

    return recommendations