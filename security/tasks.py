from celery import shared_task
from django.utils import timezone
from django.db import transaction, models
from datetime import timedelta

from .models import SuspiciousActivity, IPBlock, AnnounceLog
from accounts.models import User
from logging_monitoring.models import SystemLog, Alert


@shared_task
def auto_block_suspicious_ips():
    """مسدودی خودکار IP های مشکوک"""

    # یافتن IP هایی با فعالیت مشکوک بالا
    suspicious_ips = SuspiciousActivity.objects.filter(
        detected_at__gte=timezone.now() - timedelta(hours=24),
        severity__in=['high', 'critical']
    ).values('ip_address').annotate(
        count=models.Count('ip_address')
    ).filter(count__gte=5).order_by('-count')  # حداقل ۵ فعالیت مشکوک در ۲۴ ساعت

    blocked_count = 0
    for ip_data in suspicious_ips:
        ip_address = ip_data['ip_address']
        activity_count = ip_data['count']

        # بررسی وجود مسدودی قبلی
        if IPBlock.objects.filter(ip_address=ip_address, is_active=True).exists():
            continue

        # ایجاد مسدودی
        block = IPBlock.objects.create(
            ip_address=ip_address,
            reason=f'Automatic block: {activity_count} suspicious activities in 24 hours',
            expires_at=timezone.now() + timedelta(days=7)  # مسدودی ۷ روزه
        )

        # لاگ مسدودی
        SystemLog.objects.create(
            category='security',
            level='warning',
            message=f'Auto-blocked IP: {ip_address} ({activity_count} suspicious activities)',
            details={
                'ip_address': ip_address,
                'activity_count': activity_count,
                'expires_at': str(block.expires_at)
            }
        )

        blocked_count += 1

    return f"Auto-blocked {blocked_count} IPs"


@shared_task
def cleanup_expired_blocks():
    """پاکسازی مسدودی‌های منقضی شده"""

    expired_blocks = IPBlock.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now()
    )

    count = 0
    for block in expired_blocks:
        block.is_active = False
        block.save()

        # لاگ رفع مسدودی
        SystemLog.objects.create(
            category='security',
            level='info',
            message=f'Expired IP block removed: {block.ip_address}',
            details={'ip_address': block.ip_address}
        )

        count += 1

    return f"Cleaned up {count} expired blocks"


@shared_task
def detect_ratio_manipulators():
    """تشخیص دستکاری کنندگان ratio"""

    # یافتن کاربران با الگوی مشکوک
    suspicious_users = []

    # کاربران با آپلود ناگهانی بالا
    users_with_sudden_upload = User.objects.filter(
        lifetime_upload__gt=1024 * 1024 * 1024,  # بیش از ۱GB آپلود
        date_joined__gte=timezone.now() - timedelta(days=7)  # عضو جدید
    )

    for user in users_with_sudden_upload:
        # بررسی announce logs
        recent_logs = AnnounceLog.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(hours=24)
        )

        if recent_logs.exists():
            avg_upload_per_announce = sum(log.uploaded for log in recent_logs) / len(recent_logs)

            if avg_upload_per_announce > 100 * 1024 * 1024:  # بیش از ۱۰۰MB در هر announce
                suspicious_users.append(user)

                SuspiciousActivity.objects.create(
                    user=user,
                    activity_type='ratio_manipulation',
                    severity='high',
                    description='Potential ratio manipulation detected',
                    details={
                        'avg_upload_per_announce': avg_upload_per_announce,
                        'announce_count': len(recent_logs),
                        'account_age_days': (timezone.now() - user.date_joined).days
                    },
                    ip_address=recent_logs.first().ip_address
                )

    if suspicious_users:
        Alert.objects.create(
            alert_type='security_breach',
            priority='high',
            title='Ratio Manipulation Detected',
            message=f'{len(suspicious_users)} users showing ratio manipulation patterns',
            details={'user_count': len(suspicious_users)}
        )

    return f"Detected {len(suspicious_users)} potential ratio manipulators"


@shared_task
def monitor_abnormal_activity():
    """مانیتورینگ فعالیت‌های غیرطبیعی"""

    alerts_created = 0

    # بررسی announce های بسیار زیاد
    high_frequency_users = AnnounceLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(hours=1)
    ).values('user').annotate(
        announce_count=models.Count('id')
    ).filter(announce_count__gte=60).order_by('-announce_count')  # بیش از ۶۰ announce در ساعت

    for user_data in high_frequency_users:
        user = User.objects.get(id=user_data['user'])
        announce_count = user_data['announce_count']

        # ایجاد alert اگر قبلاً ایجاد نشده
        recent_alert = Alert.objects.filter(
            alert_type='security_breach',
            created_at__gte=timezone.now() - timedelta(hours=1),
            message__contains=f'{user.username}'
        ).exists()

        if not recent_alert:
            Alert.objects.create(
                alert_type='security_breach',
                priority='medium',
                title='High Announce Frequency',
                message=f'User {user.username}: {announce_count} announces in 1 hour',
                user=user,
                details={'announce_count': announce_count}
            )
            alerts_created += 1

    # بررسی کاربران با چندین IP
    multi_ip_users = AnnounceLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).values('user').annotate(
        ip_count=models.Count('ip_address', distinct=True)
    ).filter(ip_count__gte=5).order_by('-ip_count')  # بیش از ۵ IP مختلف

    for user_data in multi_ip_users:
        user = User.objects.get(id=user_data['user'])
        ip_count = user_data['ip_count']

        SuspiciousActivity.objects.create(
            user=user,
            activity_type='ip_spoofing',
            severity='high',
            description=f'Multiple IP addresses detected: {ip_count} IPs in 24 hours',
            details={'ip_count': ip_count},
            ip_address='multiple'
        )

    return f"Created {alerts_created} abnormal activity alerts"


@shared_task
def update_security_stats():
    """بروزرسانی آمار امنیتی"""

    from logging_monitoring.models import SystemStats

    today = timezone.now().date()

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
        stats.suspicious_activities = SuspiciousActivity.objects.filter(
            detected_at__date=today
        ).count()
        stats.blocked_ips = IPBlock.objects.filter(is_active=True).count()
        stats.save()

    return f"Updated security stats for {today}"
