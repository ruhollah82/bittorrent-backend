from django.db import models
from django.conf import settings
from django.utils import timezone


class SystemLog(models.Model):
    """لاگ سیستم"""

    LOG_LEVELS = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    LOG_CATEGORIES = [
        ('auth', 'Authentication'),
        ('tracker', 'Tracker'),
        ('credit', 'Credit'),
        ('security', 'Security'),
        ('admin', 'Admin'),
        ('system', 'System'),
    ]

    level = models.CharField(
        max_length=10,
        choices=LOG_LEVELS,
        default='info'
    )
    category = models.CharField(
        max_length=20,
        choices=LOG_CATEGORIES
    )
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.level.upper()}] {self.category}: {self.message[:50]}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['category']),
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['level', 'category', '-timestamp']),
        ]


class UserActivity(models.Model):
    """فعالیت‌های کاربران"""

    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('register', 'Register'),
        ('profile_update', 'Profile Update'),
        ('torrent_upload', 'Torrent Upload'),
        ('torrent_download', 'Torrent Download'),
        ('credit_change', 'Credit Change'),
        ('ban', 'Ban'),
        ('unban', 'Unban'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES
    )
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username}: {self.activity_type}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['ip_address']),
        ]


class SystemStats(models.Model):
    """آمار سیستم"""

    date = models.DateField(unique=True)
    total_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)  # کاربران فعال در 24 ساعت گذشته
    total_torrents = models.IntegerField(default=0)
    active_torrents = models.IntegerField(default=0)
    total_peers = models.IntegerField(default=0)
    total_upload = models.BigIntegerField(default=0)  # bytes
    total_download = models.BigIntegerField(default=0)  # bytes
    total_credit_transacted = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    suspicious_activities = models.IntegerField(default=0)
    blocked_ips = models.IntegerField(default=0)

    def __str__(self):
        return f"Stats for {self.date}"

    class Meta:
        ordering = ['-date']


class Alert(models.Model):
    """هشدارهای سیستم"""

    ALERT_TYPES = [
        ('ratio_anomaly', 'Ratio Anomaly'),
        ('credit_threshold', 'Credit Threshold'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('system_performance', 'System Performance'),
        ('security_breach', 'Security Breach'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='medium'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    torrent = models.ForeignKey(
        'torrents.Torrent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.priority.upper()}] {self.title}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_acknowledged']),
            models.Index(fields=['created_at']),
        ]
