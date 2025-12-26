from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.core.paginator import Paginator

from accounts.models import User, InviteCode, AuthToken
from credits.models import CreditTransaction
from security.models import SuspiciousActivity, IPBlock
from logging_monitoring.models import Alert, SystemLog, SystemStats
from .models import AdminAction, SystemConfig
from .serializers import (
    UserManagementSerializer, UserUpdateSerializer,
    InviteCodeManagementSerializer, BulkInviteCodeSerializer,
    SystemConfigSerializer, AdminDashboardSerializer,
    AdminReportSerializer, AdminActionSerializer,
    TorrentModerationSerializer, MassUserActionSerializer
)


class IsAdminUser(permissions.BasePermission):
    """Permission برای اطمینان از دسترسی ادمین"""

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class AdminDashboardView(generics.RetrieveAPIView):
    """نمای داشبورد ادمین"""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = AdminDashboardSerializer

    def get_object(self):
        # آمار کلی
        total_users = User.objects.count()
        total_credit_transacted = CreditTransaction.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # آمار امنیتی
        suspicious_activities_today = SuspiciousActivity.objects.filter(
            detected_at__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()

        active_ip_blocks = IPBlock.objects.filter(is_active=True).count()
        banned_users = User.objects.filter(is_banned=True).count()

        # آمار سیستم
        system_alerts = Alert.objects.filter(is_acknowledged=False).count()
        recent_logs = SystemLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()

        # کاربران اخیر (۱۰ کاربر اخیر)
        recent_users = list(User.objects.order_by('-date_joined')[:10].values(
            'id', 'username', 'date_joined', 'user_class'
        ))

        # فعالیت‌های مشکوک اخیر (۱۰ فعالیت اخیر)
        recent_suspicious = list(SuspiciousActivity.objects.order_by('-detected_at')[:10].values(
            'id', 'activity_type', 'severity', 'detected_at'
        ))

        # هشدارهای اخیر (۱۰ هشدار اخیر)
        recent_alerts = list(Alert.objects.order_by('-created_at')[:10].values(
            'id', 'title', 'priority', 'is_acknowledged', 'created_at'
        ))

        return {
            'total_users': total_users,
            'total_torrents': 0,  # TODO: implement when torrents app is complete
            'total_credit_transacted': total_credit_transacted,
            'active_peers': 0,  # TODO: implement peer counting
            'suspicious_activities_today': suspicious_activities_today,
            'active_ip_blocks': active_ip_blocks,
            'banned_users': banned_users,
            'system_alerts': system_alerts,
            'recent_logs': recent_logs,
            'recent_users': recent_users,
            'recent_suspicious': recent_suspicious,
            'recent_alerts': recent_alerts,
        }


class UserManagementListView(generics.ListAPIView):
    """نمای لیست کاربران برای مدیریت"""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = UserManagementSerializer
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.all()

        # فیلترها
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)

        email = self.request.query_params.get('email')
        if email:
            queryset = queryset.filter(email__icontains=email)

        user_class = self.request.query_params.get('user_class')
        if user_class:
            queryset = queryset.filter(user_class=user_class)

        is_banned = self.request.query_params.get('is_banned')
        if is_banned is not None:
            queryset = queryset.filter(is_banned=is_banned.lower() == 'true')

        # مرتب‌سازی
        order_by = self.request.query_params.get('order_by', '-date_joined')
        if order_by in ['username', '-username', 'date_joined', '-date_joined',
                       'total_credit', '-total_credit', 'ratio', '-ratio']:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('-date_joined')

        return queryset


class UserManagementDetailView(generics.RetrieveUpdateAPIView):
    """نمای جزئیات و بروزرسانی کاربر"""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = UserManagementSerializer
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserManagementSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        old_data = {
            'user_class': instance.user_class,
            'is_banned': instance.is_banned,
            'ban_reason': instance.ban_reason,
        }

        with transaction.atomic():
            instance = serializer.save()

            # لاگ تغییرات
            changes = []
            if old_data['user_class'] != instance.user_class:
                changes.append(f'class: {old_data["user_class"]} -> {instance.user_class}')
            if old_data['is_banned'] != instance.is_banned:
                action = 'banned' if instance.is_banned else 'unbanned'
                changes.append(f'status: {action}')
            if old_data['ban_reason'] != instance.ban_reason and instance.ban_reason:
                changes.append(f'ban_reason: {instance.ban_reason}')

            if changes:
                # لاگ در سیستم
                SystemLog.objects.create(
                    category='admin',
                    level='info',
                    message=f'User {instance.username} updated by admin',
                    details={'changes': changes, 'admin': request.user.username},
                    user=request.user
                )

                # لاگ اقدام ادمین
                AdminAction.objects.create(
                    admin=request.user,
                    action_type='user_update',
                    target_user=instance,
                    description=f'User profile updated: {", ".join(changes)}',
                    details={'changes': changes},
                    ip_address=request.META.get('REMOTE_ADDR')
                )

        return Response(serializer.data)


class InviteCodeManagementListView(generics.ListCreateAPIView):
    """نمای لیست و ایجاد کدهای دعوت"""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = InviteCodeManagementSerializer
    paginate_by = 20

    def get_queryset(self):
        queryset = InviteCode.objects.all()

        # فیلترها
        is_used = self.request.query_params.get('is_used')
        if is_used is not None:
            if is_used.lower() == 'true':
                queryset = queryset.filter(used_by__isnull=False)
            else:
                queryset = queryset.filter(used_by__isnull=True)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST' and 'count' in self.request.data:
            return BulkInviteCodeSerializer
        return InviteCodeManagementSerializer

    def create(self, request, *args, **kwargs):
        if 'count' in request.data:
            # ایجاد انبوه
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            result = serializer.save()

            # لاگ ایجاد
            SystemLog.objects.create(
                category='admin',
                level='info',
                message=f'Bulk invite codes created: {len(result["created_codes"])} codes',
                details=result,
                user=request.user
            )

            return Response(result, status=status.HTTP_201_CREATED)
        else:
            # ایجاد تک
            return super().create(request, *args, **kwargs)


class SystemConfigListView(generics.ListCreateAPIView):
    """نمای لیست و ایجاد تنظیمات سیستم"""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = SystemConfigSerializer

    def get_queryset(self):
        return SystemConfig.objects.filter(is_active=True).order_by('key')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instance = serializer.save(updated_by=request.user)

            # لاگ تغییر تنظیمات
            SystemLog.objects.create(
                category='admin',
                level='info',
                message=f'System config updated: {instance.key}',
                details={
                    'key': instance.key,
                    'value': instance.value,
                    'config_type': instance.config_type
                },
                user=request.user
            )

            AdminAction.objects.create(
                admin=request.user,
                action_type='system_config',
                description=f'System config updated: {instance.key} = {instance.value}',
                details={'config_key': instance.key, 'config_value': instance.value},
                ip_address=request.META.get('REMOTE_ADDR')
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SystemConfigDetailView(generics.RetrieveUpdateDestroyAPIView):
    """نمای جزئیات تنظیمات سیستم"""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = SystemConfigSerializer
    queryset = SystemConfig.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_value = instance.value

        response = super().update(request, *args, **kwargs)

        if instance.value != old_value:
            instance.updated_by = request.user
            instance.save()

            # لاگ تغییر
            SystemLog.objects.create(
                category='admin',
                level='info',
                message=f'System config changed: {instance.key}',
                details={
                    'key': instance.key,
                    'old_value': old_value,
                    'new_value': instance.value
                },
                user=request.user
            )

        return response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def generate_report(request):
    """تولید گزارش‌های ادمین"""

    serializer = AdminReportSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    report_type = serializer.validated_data['report_type']
    start_date = serializer.validated_data['start_date']
    end_date = serializer.validated_data['end_date']
    filters = serializer.validated_data.get('filters', {})

    report_data = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'generated_at': timezone.now(),
        'summary': {},
        'data': [],
        'charts': {}
    }

    if report_type == 'user_activity':
        # گزارش فعالیت کاربران
        users = User.objects.filter(date_joined__range=(start_date, end_date))

        report_data['summary'] = {
            'total_new_users': users.count(),
            'active_users': users.filter(last_login__gte=timezone.now() - timedelta(days=7)).count(),
            'banned_users': users.filter(is_banned=True).count(),
        }

        report_data['data'] = list(users.values(
            'id', 'username', 'email', 'user_class',
            'date_joined', 'last_login', 'is_banned'
        ))

        # نمودار ثبت‌نام روزانه
        daily_signups = users.extra(
            select={'day': "DATE(date_joined)"}
        ).values('day').annotate(count=Count('id')).order_by('day')

        report_data['charts'] = {
            'daily_signups': list(daily_signups)
        }

    elif report_type == 'security_summary':
        # گزارش خلاصه امنیتی
        suspicious = SuspiciousActivity.objects.filter(
            detected_at__date__range=(start_date, end_date)
        )

        ip_blocks = IPBlock.objects.filter(
            blocked_at__date__range=(start_date, end_date)
        )

        report_data['summary'] = {
            'total_suspicious_activities': suspicious.count(),
            'unique_suspicious_users': suspicious.values('user').distinct().count(),
            'ip_blocks_created': ip_blocks.count(),
            'currently_banned_users': User.objects.filter(is_banned=True).count(),
        }

        # فعالیت‌های مشکوک بر اساس نوع
        suspicious_by_type = suspicious.values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')

        report_data['data'] = list(suspicious_by_type)

        # نمودار فعالیت‌های مشکوک روزانه
        daily_suspicious = suspicious.extra(
            select={'day': "DATE(detected_at)"}
        ).values('day').annotate(count=Count('id')).order_by('day')

        report_data['charts'] = {
            'daily_suspicious': list(daily_suspicious)
        }

    elif report_type == 'credit_usage':
        # گزارش استفاده از credit
        transactions = CreditTransaction.objects.filter(
            created_at__date__range=(start_date, end_date),
            status='completed'
        )

        report_data['summary'] = {
            'total_transactions': transactions.count(),
            'total_credit_amount': transactions.aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'upload_transactions': transactions.filter(transaction_type='upload').count(),
            'download_transactions': transactions.filter(transaction_type='download').count(),
        }

        # تراکنش‌ها بر اساس نوع
        transactions_by_type = transactions.values('transaction_type').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('transaction_type')

        report_data['data'] = list(transactions_by_type)

        # نمودار تراکنش‌های روزانه
        daily_transactions = transactions.extra(
            select={'day': "DATE(created_at)"}
        ).values('day').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('day')

        report_data['charts'] = {
            'daily_transactions': list(daily_transactions)
        }

    # لاگ تولید گزارش
    SystemLog.objects.create(
        category='admin',
        level='info',
        message=f'Admin report generated: {report_type}',
        details={
            'report_type': report_type,
            'date_range': f'{start_date} to {end_date}',
            'admin': request.user.username
        },
        user=request.user
    )

    return Response(report_data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def mass_user_action(request):
    """اقدامات انبوه روی کاربران"""

    serializer = MassUserActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_ids = serializer.validated_data['user_ids']
    action = serializer.validated_data['action']
    reason = serializer.validated_data.get('reason', '')
    new_class = serializer.validated_data.get('new_class')

    users = User.objects.filter(id__in=user_ids)
    affected_count = 0

    with transaction.atomic():
        if action == 'ban':
            affected_count = users.update(is_banned=True, ban_reason=reason)
        elif action == 'unban':
            affected_count = users.update(is_banned=False, ban_reason='')
        elif action == 'change_class':
            affected_count = users.update(user_class=new_class)
        elif action == 'reset_ratio':
            # تنظیم lifetime_upload و download به 0 برای reset ratio
            affected_count = users.update(lifetime_upload=0, lifetime_download=0)

        if affected_count > 0:
            # لاگ اقدام انبوه
            SystemLog.objects.create(
                category='admin',
                level='warning',
                message=f'Mass user action: {action} on {affected_count} users',
                details={
                    'action': action,
                    'user_count': affected_count,
                    'user_ids': user_ids,
                    'reason': reason,
                    'new_class': new_class
                },
                user=request.user
            )

            AdminAction.objects.create(
                admin=request.user,
                action_type='mass_user_action',
                description=f'Mass action: {action} on {affected_count} users',
                details={
                    'action': action,
                    'user_count': affected_count,
                    'reason': reason
                },
                ip_address=request.META.get('REMOTE_ADDR')
            )

    return Response({
        'success': True,
        'action': action,
        'affected_users': affected_count,
        'total_requested': len(user_ids)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_actions_log(request):
    """لاگ اقدامات ادمین"""

    queryset = AdminAction.objects.all()

    # فیلترها
    action_type = request.query_params.get('action_type')
    if action_type:
        queryset = queryset.filter(action_type=action_type)

    admin_id = request.query_params.get('admin_id')
    if admin_id:
        queryset = queryset.filter(admin_id=admin_id)

    # صفحه‌بندی
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))

    paginator = Paginator(queryset.order_by('-timestamp'), per_page)

    try:
        actions_page = paginator.page(page)
    except:
        return Response({'error': 'Invalid page'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = AdminActionSerializer(actions_page, many=True)

    return Response({
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page,
        'results': serializer.data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def system_maintenance(request):
    """عملیات نگهداری سیستم"""

    action = request.data.get('action')

    if action == 'cleanup_old_data':
        # پاکسازی داده‌های قدیمی
        from logging_monitoring.tasks import cleanup_old_logs

        result = cleanup_old_logs()
        message = f"Cleanup completed: {result}"

    elif action == 'update_stats':
        # بروزرسانی آمار
        from logging_monitoring.tasks import update_daily_stats

        result = update_daily_stats()
        message = f"Stats updated: {result}"

    elif action == 'generate_report':
        # تولید گزارش سیستم
        from logging_monitoring.tasks import generate_system_report

        result = generate_system_report()
        message = f"Report generated: {result}"

    else:
        return Response(
            {'error': 'Invalid action'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # لاگ عملیات نگهداری
    SystemLog.objects.create(
        category='admin',
        level='info',
        message=f'System maintenance: {action}',
        details={'action': action, 'result': message},
        user=request.user
    )

    return Response({
        'success': True,
        'action': action,
        'message': message
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def advanced_analytics(request):
    """آمار پیشرفته سیستم"""

    # دوره زمانی
    days = int(request.GET.get('days', 30))

    since_date = timezone.now() - timedelta(days=days)

    # آمار کاربران
    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=since_date).count()
    new_users = User.objects.filter(date_joined__gte=since_date).count()

    # آمار تورنت
    total_torrents = Torrent.objects.count()
    active_torrents = Torrent.objects.filter(is_active=True).count()
    new_torrents = Torrent.objects.filter(created_at__gte=since_date).count()

    # آمار credit
    total_credit_transacted = CreditTransaction.objects.filter(
        created_at__gte=since_date,
        status='completed'
    ).aggregate(
        total=Sum('amount'),
        uploads=Sum('amount', filter=Q(transaction_type='upload')),
        downloads=Sum('amount', filter=Q(transaction_type='download')),
        bonuses=Sum('amount', filter=Q(transaction_type='bonus'))
    )

    # آمار tracker
    total_announces = AnnounceLog.objects.filter(timestamp__gte=since_date).count()
    unique_peers = Peer.objects.filter(
        last_announced__gte=since_date
    ).values('ip_address').distinct().count()

    # توزیع کاربران بر اساس کلاس
    user_class_distribution = User.objects.values('user_class').annotate(
        count=Count('id')
    ).order_by('user_class')

    # محبوب‌ترین دسته‌بندی‌ها
    popular_categories = Torrent.objects.filter(
        is_active=True,
        created_at__gte=since_date
    ).values('category').annotate(
        count=Count('id'),
        total_size=Sum('size')
    ).order_by('-count')[:10]

    # نرخ رشد روزانه (آخرین 7 روز)
    daily_growth = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        next_date = date + timedelta(days=1)

        daily_users = User.objects.filter(
            date_joined__date=date
        ).count()

        daily_torrents = Torrent.objects.filter(
            created_at__date=date
        ).count()

        daily_credits = CreditTransaction.objects.filter(
            created_at__date=date,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        daily_growth.append({
            'date': date.isoformat(),
            'new_users': daily_users,
            'new_torrents': daily_torrents,
            'credit_volume': float(daily_credits)
        })

    return Response({
        'period_days': days,
        'user_stats': {
            'total_users': total_users,
            'active_users': active_users,
            'new_users': new_users,
            'user_class_distribution': list(user_class_distribution)
        },
        'torrent_stats': {
            'total_torrents': total_torrents,
            'active_torrents': active_torrents,
            'new_torrents': new_torrents,
            'popular_categories': list(popular_categories)
        },
        'credit_stats': {
            'total_transacted': float(total_credit_transacted['total'] or 0),
            'upload_credits': float(total_credit_transacted['uploads'] or 0),
            'download_credits': float(total_credit_transacted['downloads'] or 0),
            'bonus_credits': float(total_credit_transacted['bonuses'] or 0)
        },
        'tracker_stats': {
            'total_announces': total_announces,
            'unique_peers': unique_peers
        },
        'daily_growth': daily_growth
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def bulk_torrent_moderation(request):
    """مدیریت انبوه تورنت‌ها"""

    action = request.data.get('action')
    torrent_ids = request.data.get('torrent_ids', [])
    reason = request.data.get('reason', '')

    if not action or not torrent_ids:
        return Response(
            {'error': 'action and torrent_ids are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    valid_actions = ['activate', 'deactivate', 'delete', 'change_category']
    if action not in valid_actions:
        return Response(
            {'error': f'Invalid action. Valid actions: {valid_actions}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    torrents = Torrent.objects.filter(id__in=torrent_ids)

    if action == 'activate':
        updated = torrents.update(is_active=True)
        action_type = 'torrent_activate'
    elif action == 'deactivate':
        updated = torrents.update(is_active=False)
        action_type = 'torrent_deactivate'
    elif action == 'delete':
        # Soft delete by deactivating
        updated = torrents.update(is_active=False)
        action_type = 'torrent_delete'
    elif action == 'change_category':
        new_category = request.data.get('new_category')
        if not new_category:
            return Response({'error': 'new_category required for change_category action'})
        updated = torrents.update(category=new_category)
        action_type = 'torrent_category_change'

    # Log the admin action
    AdminAction.objects.create(
        admin=request.user,
        action_type=action_type,
        description=f'Bulk {action} of {updated} torrents',
        details={
            'torrent_ids': torrent_ids,
            'action': action,
            'reason': reason,
            'affected_count': updated
        }
    )

    return Response({
        'success': True,
        'action': action,
        'affected_count': updated,
        'torrent_ids': torrent_ids
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def system_cleanup(request):
    """پاکسازی سیستم"""

    cleanup_type = request.data.get('cleanup_type')
    days_old = int(request.data.get('days_old', 30))

    if cleanup_type not in ['logs', 'inactive_torrents', 'old_peers', 'all']:
        return Response({'error': 'Invalid cleanup_type'}, status=status.HTTP_400_BAD_REQUEST)

    cutoff_date = timezone.now() - timedelta(days=days_old)
    results = {}

    with transaction.atomic():
        if cleanup_type in ['logs', 'all']:
            # پاکسازی لاگ‌های قدیمی
            old_logs = SystemLog.objects.filter(timestamp__lt=cutoff_date).delete()
            old_activities = UserActivity.objects.filter(timestamp__lt=cutoff_date).delete()
            results['logs_deleted'] = old_logs[0] + old_activities[0]

        if cleanup_type in ['inactive_torrents', 'all']:
            # غیرفعال کردن تورنت‌های قدیمی بدون peer
            old_torrents = Torrent.objects.filter(
                is_active=True,
                created_at__lt=cutoff_date,
                peers__isnull=True
            ).update(is_active=False)
            results['torrents_deactivated'] = old_torrents

        if cleanup_type in ['old_peers', 'all']:
            # پاکسازی peerهای قدیمی
            old_peers = Peer.objects.filter(last_announced__lt=cutoff_date).delete()
            results['peers_deleted'] = old_peers[0]

    # Log the cleanup action
    AdminAction.objects.create(
        admin=request.user,
        action_type='system_cleanup',
        description=f'System cleanup: {cleanup_type}',
        details={
            'cleanup_type': cleanup_type,
            'days_old': days_old,
            'results': results
        }
    )

    return Response({
        'success': True,
        'cleanup_type': cleanup_type,
        'days_old': days_old,
        'results': results
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def system_performance_metrics(request):
    """متریک‌های عملکرد سیستم"""

    # Database performance
    from django.db import connection
    with connection.cursor() as cursor:
        # تعداد اتصالات فعال (SQLite compatible)
        try:
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
            active_connections = cursor.fetchone()[0]
        except:
            active_connections = 1  # SQLite doesn't have connection stats

        # اندازه database (approximate)
        try:
            cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size();")
            db_size = cursor.fetchone()[0]
        except:
            db_size = 0

    # Cache performance (basic)
    cache_stats = {
        'status': 'basic',
        'note': 'Advanced cache metrics require Redis/memcached'
    }

    # System resources
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=0.1)

        system_resources = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': disk.percent,
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2)
        }
    except ImportError:
        system_resources = {'error': 'psutil not available for system metrics'}

    # Application metrics
    app_metrics = {
        'total_users': User.objects.count(),
        'active_users_24h': User.objects.filter(last_login__gte=timezone.now() - timedelta(hours=24)).count(),
        'total_torrents': Torrent.objects.count(),
        'active_torrents': Torrent.objects.filter(is_active=True).count(),
        'total_peers': Peer.objects.filter(last_announced__gte=timezone.now() - timedelta(hours=1)).count(),
        'credit_transactions_24h': CreditTransaction.objects.filter(created_at__gte=timezone.now() - timedelta(hours=24)).count(),
        'system_logs_24h': SystemLog.objects.filter(timestamp__gte=timezone.now() - timedelta(hours=24)).count(),
        'tracker_announces_1h': AnnounceLog.objects.filter(timestamp__gte=timezone.now() - timedelta(hours=1)).count()
    }

    return Response({
        'database': {
            'estimated_connections': active_connections,
            'estimated_size_bytes': db_size,
            'estimated_size_mb': round(db_size / (1024**2), 2) if db_size else 0
        },
        'cache': cache_stats,
        'system_resources': system_resources,
        'application': app_metrics,
        'timestamp': timezone.now(),
        'uptime_seconds': 0  # Would need to track application start time
    })