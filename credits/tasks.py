from celery import shared_task
from django.utils import timezone
from django.db import transaction
from accounts.models import User
from logging_monitoring.models import SystemLog, Alert


@shared_task
def update_user_classes():
    """بروزرسانی خودکار کلاس کاربران"""

    users = User.objects.all()
    updated_count = 0

    for user in users:
        old_class = user.user_class
        new_class = calculate_user_class(user)

        if new_class != old_class:
            user.user_class = new_class
            user.save(update_fields=['user_class'])
            updated_count += 1

            # لاگ ارتقا
            SystemLog.objects.create(
                category='system',
                level='info',
                message=f'User {user.username} automatically promoted to {new_class}',
                details={
                    'user_id': user.id,
                    'old_class': old_class,
                    'new_class': new_class,
                    'ratio': user.ratio,
                    'upload': user.lifetime_upload
                },
                user=user
            )

    return f"Updated {updated_count} users"


@shared_task
def check_ratio_alerts():
    """بررسی هشدارهای ratio"""

    # کاربران با ratio پایین
    low_ratio_users = User.objects.filter(
        lifetime_download__gt=1024 * 1024 * 1024  # بیش از 1GB دانلود
    ).exclude(
        ratio__gte=0.5
    )

    alerts_created = 0
    for user in low_ratio_users:
        # بررسی وجود alert اخیر
        recent_alert = Alert.objects.filter(
            user=user,
            alert_type='ratio_anomaly',
            created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).exists()

        if not recent_alert:
            priority = 'medium' if user.ratio >= 0.2 else 'high'

            Alert.objects.create(
                alert_type='ratio_anomaly',
                priority=priority,
                title=f'Low Ratio Alert: {user.username}',
                message=f'User {user.username} has ratio {user.ratio:.3f}',
                user=user,
                details={
                    'ratio': user.ratio,
                    'upload': user.lifetime_upload,
                    'download': user.lifetime_download
                }
            )
            alerts_created += 1

    return f"Created {alerts_created} ratio alerts"


@shared_task
def cleanup_old_transactions():
    """پاکسازی تراکنش‌های قدیمی"""

    from .models import CreditTransaction
    from django.utils import timezone

    # پاکسازی تراکنش‌های موفق قدیمی‌تر از 90 روز
    cutoff_date = timezone.now() - timezone.timedelta(days=90)

    deleted_count = CreditTransaction.objects.filter(
        status='completed',
        created_at__lt=cutoff_date
    ).delete()[0]

    return f"Cleaned up {deleted_count} old transactions"


def calculate_user_class(user):
    """محاسبه کلاس کاربر بر اساس عملکرد"""

    # Elite
    if (user.ratio >= 2.0 and
        user.lifetime_upload >= 500 * 1024 * 1024 * 1024 and  # 500GB
        (timezone.now() - user.date_joined).days >= 90):
        return 'elite'

    # Trusted
    if (user.ratio >= 1.0 and
        user.lifetime_upload >= 100 * 1024 * 1024 * 1024 and  # 100GB
        (timezone.now() - user.date_joined).days >= 30):
        return 'trusted'

    # Member
    if (user.ratio >= 0.5 and
        user.lifetime_upload >= 10 * 1024 * 1024 * 1024 and  # 10GB
        (timezone.now() - user.date_joined).days >= 7):
        return 'member'

    # Newbie (default)
    return 'newbie'
