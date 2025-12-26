from django.db import models
from django.conf import settings
from django.utils import timezone


class AdminAction(models.Model):
    """لاگ اقدامات ادمین"""

    ACTION_TYPES = [
        ('user_ban', 'User Ban'),
        ('user_unban', 'User Unban'),
        ('credit_adjust', 'Credit Adjustment'),
        ('torrent_remove', 'Torrent Removal'),
        ('invite_create', 'Invite Creation'),
        ('system_config', 'System Configuration'),
    ]

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_actions'
    )
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_actions_received'
    )
    target_torrent = models.ForeignKey(
        'torrents.Torrent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.admin.username}: {self.action_type}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['admin', '-timestamp']),
            models.Index(fields=['action_type']),
            models.Index(fields=['target_user']),
        ]


class SystemConfig(models.Model):
    """تنظیمات سیستم قابل تغییر توسط ادمین"""

    CONFIG_TYPES = [
        ('global', 'Global Setting'),
        ('user_class', 'User Class Setting'),
        ('torrent', 'Torrent Setting'),
        ('security', 'Security Setting'),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()  # JSON string
    config_type = models.CharField(
        max_length=20,
        choices=CONFIG_TYPES,
        default='global'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='config_updates'
    )

    def __str__(self):
        return f"Config: {self.key}"

    class Meta:
        ordering = ['key']
