from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
from django.db import connection
from collections import defaultdict

from .models import SystemLog, UserActivity, SystemStats, Alert
from .serializers import (
    SystemLogSerializer, UserActivitySerializer,
    SystemStatsSerializer, AlertSerializer,
    DashboardStatsSerializer, LogAnalysisSerializer
)
from accounts.models import User
from credits.models import CreditTransaction
from security.models import SuspiciousActivity, IPBlock, AnnounceLog


class SystemLogListView(generics.ListAPIView):
    """نمای لیست لاگ های سیستم"""

    serializer_class = SystemLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    paginate_by = 50

    def get_queryset(self):
        queryset = SystemLog.objects.all()

        # فیلترها
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        return queryset.order_by('-timestamp')


class UserActivityListView(generics.ListAPIView):
    """نمای لیست فعالیت های کاربران"""

    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    paginate_by = 50

    def get_queryset(self):
        queryset = UserActivity.objects.all()

        # فیلترها
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        activity_type = self.request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)

        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        return queryset.order_by('-timestamp')


class AlertListView(generics.ListAPIView):
    """نمای لیست هشدارها"""

    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    paginate_by = 20

    def get_queryset(self):
        queryset = Alert.objects.all()

        # فیلترها
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        acknowledged = self.request.query_params.get('acknowledged')
        if acknowledged is not None:
            queryset = queryset.filter(is_acknowledged=acknowledged.lower() == 'true')

        return queryset.order_by('-created_at')


class AlertDetailView(generics.RetrieveUpdateAPIView):
    """نمای جزئیات هشدار"""

    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        acknowledged = request.data.get('is_acknowledged', False)

        if acknowledged and not instance.is_acknowledged:
            instance.is_acknowledged = True
            instance.acknowledged_at = timezone.now()
            instance.acknowledged_by = request.user
            instance.save()

            # لاگ acknowledge
            SystemLog.objects.create(
                category='admin',
                level='info',
                message=f'Alert acknowledged by {request.user.username}',
                details={'alert_id': instance.id, 'alert_title': instance.title},
                user=request.user
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class SystemStatsListView(generics.ListAPIView):
    """نمای لیست آمار سیستم"""

    serializer_class = SystemStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SystemStats.objects.all().order_by('-date')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """آمار داشبورد"""

    # آمار کاربران
    total_users = User.objects.count()
    active_users_24h = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(hours=24)
    ).count()
    new_users_7d = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=7)
    ).count()

    # آمار تورنت (TODO: از torrents app)
    total_torrents = 0
    active_torrents = 0

    # آمار credit
    total_credit_transacted = CreditTransaction.objects.filter(
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # آمار امنیتی
    suspicious_activities_24h = SuspiciousActivity.objects.filter(
        detected_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    active_ip_blocks = IPBlock.objects.filter(is_active=True).count()
    alerts_unacknowledged = Alert.objects.filter(is_acknowledged=False).count()

    # آمار سیستم
    system_logs_24h = SystemLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).count()
    announce_logs_24h = AnnounceLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).count()

    # روندها (۷ روز اخیر)
    user_growth_trend = []
    credit_trend = []
    activity_trend = []

    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)

        # رشد کاربران
        users_on_date = User.objects.filter(date_joined__date=date).count()
        user_growth_trend.append({
            'date': date.isoformat(),
            'count': users_on_date
        })

        # تراکنش‌های credit
        credit_on_date = CreditTransaction.objects.filter(
            created_at__date=date,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        credit_trend.append({
            'date': date.isoformat(),
            'amount': float(credit_on_date)
        })

        # فعالیت‌ها
        activities_on_date = UserActivity.objects.filter(
            timestamp__date=date
        ).count()
        activity_trend.append({
            'date': date.isoformat(),
            'count': activities_on_date
        })

    # معکوس کردن لیست‌ها برای نمایش از قدیمی به جدید
    user_growth_trend.reverse()
    credit_trend.reverse()
    activity_trend.reverse()

    data = {
        'total_users': total_users,
        'active_users_24h': active_users_24h,
        'new_users_7d': new_users_7d,
        'total_torrents': total_torrents,
        'active_torrents': active_torrents,
        'total_credit_transacted': total_credit_transacted,
        'suspicious_activities_24h': suspicious_activities_24h,
        'active_ip_blocks': active_ip_blocks,
        'alerts_unacknowledged': alerts_unacknowledged,
        'system_logs_24h': system_logs_24h,
        'announce_logs_24h': announce_logs_24h,
        'user_growth_trend': user_growth_trend,
        'credit_trend': credit_trend,
        'activity_trend': activity_trend,
    }

    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_logs(request):
    """تحلیل لاگ ها"""

    analysis_type = request.data.get('analysis_type', 'general')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    filters = request.data.get('filters', {})

    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    start_date = timezone.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_date = timezone.datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    results = {}
    insights = []

    if analysis_type == 'general':
        # تحلیل کلی
        results['system_logs'] = SystemLog.objects.filter(
            timestamp__range=(start_date, end_date)
        ).aggregate(
            total=Count('id'),
            by_level=Count('level'),
            by_category=Count('category')
        )

        results['user_activities'] = UserActivity.objects.filter(
            timestamp__range=(start_date, end_date)
        ).aggregate(
            total=Count('id'),
            by_type=Count('activity_type')
        )

        results['alerts'] = Alert.objects.filter(
            created_at__range=(start_date, end_date)
        ).aggregate(
            total=Count('id'),
            unacknowledged=Count('id', filter=Q(is_acknowledged=False))
        )

    elif analysis_type == 'security':
        # تحلیل امنیتی
        results['suspicious_activities'] = SuspiciousActivity.objects.filter(
            detected_at__range=(start_date, end_date)
        ).aggregate(
            total=Count('id'),
            by_type=Count('activity_type'),
            by_severity=Count('severity')
        )

        results['ip_blocks'] = IPBlock.objects.filter(
            blocked_at__range=(start_date, end_date)
        ).aggregate(total=Count('id'))

        # یافتن IP های مشکوک برتر
        top_ips = SuspiciousActivity.objects.filter(
            detected_at__range=(start_date, end_date)
        ).values('ip_address').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        results['top_suspicious_ips'] = list(top_ips)

        insights.append(f"Found {len(top_ips)} suspicious IPs in the period")

    elif analysis_type == 'performance':
        # تحلیل عملکرد
        results['announce_logs'] = AnnounceLog.objects.filter(
            timestamp__range=(start_date, end_date)
        ).aggregate(
            total=Count('id'),
            suspicious=Count('id', filter=Q(is_suspicious=True))
        )

        # میانگین زمان پاسخ (اگر لاگ وجود داشته باشد)
        results['response_times'] = {
            'avg_response_time': 0,  # TODO: implement if we have response time logging
        }

    elif analysis_type == 'user_behavior':
        # تحلیل رفتار کاربران
        user_id = filters.get('user_id')
        if user_id:
            user_logs = UserActivity.objects.filter(
                user_id=user_id,
                timestamp__range=(start_date, end_date)
            )

            results['user_activities'] = list(user_logs.values(
                'activity_type', 'timestamp'
            ).order_by('timestamp'))

            results['activity_summary'] = user_logs.values('activity_type').annotate(
                count=Count('id')
            ).order_by('-count')

            insights.append(f"User {user_id} had {user_logs.count()} activities")

    response_data = {
        'analysis_type': analysis_type,
        'start_date': start_date,
        'end_date': end_date,
        'filters': filters,
        'results': results,
        'insights': insights,
        'generated_at': timezone.now(),
    }

    return Response(response_data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_manual_alert(request):
    """ایجاد هشدار دستی"""

    if not request.user.is_staff:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    alert_type = request.data.get('alert_type')
    priority = request.data.get('priority', 'medium')
    title = request.data.get('title')
    message = request.data.get('message')
    user_id = request.data.get('user_id')
    torrent_id = request.data.get('torrent_id')

    if not alert_type or not title or not message:
        return Response(
            {'error': 'alert_type, title, and message are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # بررسی مقادیر معتبر
    if alert_type not in dict(Alert.ALERT_TYPES):
        return Response(
            {'error': 'Invalid alert_type'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if priority not in dict(Alert.PRIORITY_LEVELS):
        return Response(
            {'error': 'Invalid priority'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # یافتن کاربر/تورنت اگر مشخص شده
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    torrent = None
    if torrent_id:
        # TODO: implement when torrents app is complete
        pass

    # ایجاد هشدار
    alert = Alert.objects.create(
        alert_type=alert_type,
        priority=priority,
        title=title,
        message=message,
        user=user,
        torrent=torrent,
        details={'created_by': request.user.username, 'manual': True}
    )

    # لاگ ایجاد هشدار
    SystemLog.objects.create(
        category='admin',
        level='info',
        message=f'Manual alert created: {title}',
        details={
            'alert_id': alert.id,
            'alert_type': alert_type,
            'priority': priority
        },
        user=request.user
    )

    serializer = AlertSerializer(alert)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def system_health_check(request):
    """بررسی سلامت سیستم"""

    health_status = {
        'status': 'healthy',
        'checks': {},
        'timestamp': timezone.now(),
    }

    issues = []

    # بررسی اتصال پایگاه داده
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = 'error'
        issues.append(f'Database error: {str(e)}')

    # بررسی تعداد کاربران فعال
    active_users = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(hours=24)
    ).count()
    health_status['checks']['active_users'] = active_users

    if active_users == 0:
        issues.append('No active users in the last 24 hours')

    # بررسی هشدارهای فعال
    unacked_alerts = Alert.objects.filter(
        is_acknowledged=False,
        priority__in=['high', 'critical']
    ).count()
    health_status['checks']['unacknowledged_alerts'] = unacked_alerts

    if unacked_alerts > 0:
        issues.append(f'{unacked_alerts} unacknowledged high/critical alerts')

    # بررسی فعالیت‌های مشکوک اخیر
    recent_suspicious = SuspiciousActivity.objects.filter(
        detected_at__gte=timezone.now() - timedelta(hours=1)
    ).count()
    health_status['checks']['recent_suspicious_activities'] = recent_suspicious

    if recent_suspicious > 10:
        issues.append(f'High suspicious activity: {recent_suspicious} in last hour')
        health_status['status'] = 'warning'

    # بررسی مسدودی‌های IP فعال
    active_blocks = IPBlock.objects.filter(is_active=True).count()
    health_status['checks']['active_ip_blocks'] = active_blocks

    if active_blocks > 50:
        issues.append(f'Too many active IP blocks: {active_blocks}')

    # تعیین وضعیت کلی
    if issues:
        if any('critical' in issue.lower() or 'error' in issue.lower() for issue in issues):
            health_status['status'] = 'critical'
        elif health_status['status'] != 'critical':
            health_status['status'] = 'warning'

    health_status['issues'] = issues

    return Response(health_status)