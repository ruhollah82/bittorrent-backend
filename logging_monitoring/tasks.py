from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.db.models import Count, Sum, Q

from .models import SystemStats, SystemLog
from accounts.models import User
from credits.models import CreditTransaction
from security.models import SuspiciousActivity, IPBlock


@shared_task
def update_daily_stats():
    """بروزرسانی آمار روزانه سیستم"""

    today = timezone.now().date()

    with transaction.atomic():
        # دریافت یا ایجاد آمار امروز
        stats, created = SystemStats.objects.get_or_create(
            date=today,
            defaults={
                'total_users': User.objects.count(),
                'active_users': User.objects.filter(
                    last_login__gte=timezone.now() - timedelta(days=1)
                ).count(),
                'total_torrents': 0,  # TODO: از torrents app
                'active_torrents': 0,
                'total_peers': 0,
                'suspicious_activities': SuspiciousActivity.objects.filter(
                    detected_at__date=today
                ).count(),
                'blocked_ips': IPBlock.objects.filter(is_active=True).count()
            }
        )

        if not created:
            # بروزرسانی آمار موجود
            stats.total_users = User.objects.count()
            stats.active_users = User.objects.filter(
                last_login__gte=timezone.now() - timedelta(days=1)
            ).count()
            stats.suspicious_activities = SuspiciousActivity.objects.filter(
                detected_at__date=today
            ).count()
            stats.blocked_ips = IPBlock.objects.filter(is_active=True).count()

            # محاسبه آمار credit
            credit_stats = CreditTransaction.objects.filter(
                created_at__date=today,
                status='completed'
            ).aggregate(
                total_upload=Sum('amount', filter=Q(transaction_type='upload')),
                total_download=Sum('amount', filter=Q(transaction_type='download'))
            )

            stats.total_upload = credit_stats['total_upload'] or 0
            stats.total_download = credit_stats['total_download'] or 0
            stats.total_credit_transacted = (credit_stats['total_upload'] or 0) + (credit_stats['total_download'] or 0)

            stats.save()

    return f"Updated daily stats for {today}"


@shared_task
def cleanup_old_logs():
    """پاکسازی لاگ های قدیمی"""

    # پاکسازی لاگ های سیستم قدیمی‌تر از 90 روز
    cutoff_date = timezone.now() - timedelta(days=90)

    system_logs_deleted = SystemLog.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()[0]

    # پاکسازی فعالیت‌های کاربر قدیمی‌تر از 180 روز
    from .models import UserActivity
    activity_cutoff = timezone.now() - timedelta(days=180)

    activities_deleted = UserActivity.objects.filter(
        timestamp__lt=activity_cutoff
    ).delete()[0]

    # پاکسازی هشدارهای قدیمی‌تر از 30 روز
    from .models import Alert
    alert_cutoff = timezone.now() - timedelta(days=30)

    alerts_deleted = Alert.objects.filter(
        created_at__lt=alert_cutoff,
        is_acknowledged=True
    ).delete()[0]

    return f"Cleaned up {system_logs_deleted} system logs, {activities_deleted} activities, {alerts_deleted} alerts"


@shared_task
def generate_system_report():
    """تولید گزارش روزانه سیستم"""

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    # آمار امروز
    today_stats = {
        'users': User.objects.filter(date_joined__date=today).count(),
        'logins': User.objects.filter(last_login__date=today).count(),
        'system_logs': SystemLog.objects.filter(timestamp__date=today).count(),
        'suspicious_activities': SuspiciousActivity.objects.filter(detected_at__date=today).count(),
        'credit_transactions': CreditTransaction.objects.filter(created_at__date=today).count(),
    }

    # مقایسه با دیروز
    yesterday_stats = {
        'users': User.objects.filter(date_joined__date=yesterday).count(),
        'logins': User.objects.filter(last_login__date=yesterday).count(),
        'system_logs': SystemLog.objects.filter(timestamp__date=yesterday).count(),
        'suspicious_activities': SuspiciousActivity.objects.filter(detected_at__date=yesterday).count(),
        'credit_transactions': CreditTransaction.objects.filter(created_at__date=yesterday).count(),
    }

    # محاسبه تغییرات درصدی
    changes = {}
    for key in today_stats:
        if yesterday_stats[key] > 0:
            change = ((today_stats[key] - yesterday_stats[key]) / yesterday_stats[key]) * 100
            changes[key] = round(change, 2)
        else:
            changes[key] = 0 if today_stats[key] == 0 else 100

    # ایجاد گزارش در لاگ سیستم
    report_message = f"Daily System Report - {today}"
    report_details = {
        'today_stats': today_stats,
        'yesterday_stats': yesterday_stats,
        'changes_percent': changes,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(last_login__gte=timezone.now() - timedelta(days=7)).count(),
        'total_credit': CreditTransaction.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0,
    }

    SystemLog.objects.create(
        category='system',
        level='info',
        message=report_message,
        details=report_details
    )

    return f"Generated daily report for {today}"


@shared_task
def monitor_performance():
    """مانیتورینگ عملکرد سیستم"""

    # بررسی زمان پاسخ API های اخیر
    # TODO: implement if we add response time logging

    # بررسی استفاده از پایگاه داده
    from django.db import connection
    queries_count = len(connection.queries)

    # بررسی تعداد اتصالات فعال
    # TODO: implement based on database backend

    # ایجاد هشدار اگر عملکرد پایین باشد
    if queries_count > 1000:  # تعداد کوئری های زیاد در یک task
        from .models import Alert
        Alert.objects.create(
            alert_type='system_performance',
            priority='medium',
            title='High Database Queries',
            message=f'Detected {queries_count} database queries in a single operation',
            details={'queries_count': queries_count}
        )

    return f"Performance check completed, {queries_count} queries executed"
