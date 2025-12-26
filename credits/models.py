from django.db import models
from django.conf import settings
from django.utils import timezone


class CreditTransaction(models.Model):
    """مدل تراکنش‌های credit"""

    TRANSACTION_TYPES = [
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
        ('admin_adjust', 'Admin Adjustment'),
        ('invite_bonus', 'Invite Bonus'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credit_transactions'
    )
    torrent = models.ForeignKey(
        'torrents.Torrent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='completed'
    )
    created_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}: {self.transaction_type} {self.amount}"

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.processed_at:
            self.processed_at = timezone.now()
            # بروزرسانی اعتبار کاربر
            if self.transaction_type in ['upload', 'bonus', 'invite_bonus', 'admin_adjust']:
                self.user.total_credit += self.amount
            elif self.transaction_type in ['download', 'penalty']:
                self.user.total_credit -= self.amount
            self.user.save(update_fields=['total_credit'])
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['transaction_type', 'status']),
        ]


class UserCredit(models.Model):
    """مدل آمار credit کاربر (برای کوئری‌های سریع‌تر)"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credit_stats'
    )
    total_earned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    total_spent = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    last_updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Credit stats for {self.user.username}"

    @property
    def net_credit(self):
        return self.total_earned - self.total_spent

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
