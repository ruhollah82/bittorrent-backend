from django.db import models
from django.conf import settings
from django.utils import timezone


class SuspiciousActivity(models.Model):
    """مدل فعالیت‌های مشکوک"""

    ACTIVITY_TYPES = [
        ('fake_upload', 'Fake Upload'),
        ('abnormal_ratio', 'Abnormal Ratio'),
        ('announce_flood', 'Announce Flood'),
        ('ip_spoofing', 'IP Spoofing'),
        ('invalid_peer_id', 'Invalid Peer ID'),
        ('token_abuse', 'Token Abuse'),
        ('ratio_manipulation', 'Ratio Manipulation'),
    ]

    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suspicious_activities'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='low'
    )
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)  # اطلاعات اضافی
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=200, blank=True)
    torrent = models.ForeignKey(
        'torrents.Torrent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    detected_at = models.DateTimeField(default=timezone.now)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_activities'
    )

    def __str__(self):
        return f"{self.activity_type} by {self.user.username}"

    class Meta:
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['user', '-detected_at']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_resolved']),
        ]


class AnnounceLog(models.Model):
    """لاگ announce ها برای تحلیل الگوها"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announce_logs'
    )
    torrent = models.ForeignKey(
        'torrents.Torrent',
        on_delete=models.CASCADE,
        related_name='announce_logs'
    )
    event = models.CharField(max_length=20)  # started, stopped, completed, etc.
    uploaded = models.BigIntegerField()
    downloaded = models.BigIntegerField()
    left = models.BigIntegerField()
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField()
    peer_id = models.CharField(max_length=40)
    user_agent = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    is_suspicious = models.BooleanField(default=False)
    suspicious_reason = models.TextField(blank=True)

    def __str__(self):
        return f"Announce: {self.user.username} - {self.event}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['torrent', '-timestamp']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['is_suspicious']),
            # Composite index for rate limiting
            models.Index(fields=['user', 'timestamp']),
        ]


class IPBlock(models.Model):
    """لیست IP های مسدود شده"""

    ip_address = models.GenericIPAddressField(unique=True)
    blocked_at = models.DateTimeField(default=timezone.now)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='blocked_ips'
    )
    reason = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Blocked IP: {self.ip_address}"

    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    class Meta:
        ordering = ['-blocked_at']


class RateLimit(models.Model):
    """مدیریت rate limiting"""

    identifier = models.CharField(max_length=100)  # user_id, ip, etc.
    limit_type = models.CharField(max_length=50)  # announce, api, etc.
    count = models.IntegerField(default=0)
    window_start = models.DateTimeField(default=timezone.now)
    window_end = models.DateTimeField()

    def __str__(self):
        return f"Rate limit: {self.identifier} - {self.limit_type}"

    class Meta:
        unique_together = ['identifier', 'limit_type', 'window_start']
        indexes = [
            models.Index(fields=['identifier', 'limit_type']),
            models.Index(fields=['window_end']),
        ]
