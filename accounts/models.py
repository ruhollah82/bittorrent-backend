from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
import secrets
import string


class InviteCode(models.Model):
    """مدل کد دعوت برای ثبت‌نام خصوصی"""

    code = models.CharField(max_length=32, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invites'
    )
    used_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invite'
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"InviteCode: {self.code}"

    def save(self, *args, **kwargs):
        """تولید کد منحصر به فرد در صورت خالی بودن"""
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def generate_unique_code(self):
        """تولید کد منحصر به فرد"""
        while True:
            # تولید کد 12 کاراکتری
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits)
                          for _ in range(12))
            if not InviteCode.objects.filter(code=code).exists():
                return code

    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def is_used(self):
        return self.used_by is not None

    class Meta:
        ordering = ['-created_at']


class User(AbstractUser):
    """مدل کاربر سفارشی"""

    USER_CLASSES = [
        ('newbie', 'Newbie'),
        ('member', 'Member'),
        ('trusted', 'Trusted'),
        ('elite', 'Elite'),
    ]

    user_class = models.CharField(
        max_length=10,
        choices=USER_CLASSES,
        default='newbie'
    )
    total_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    locked_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    lifetime_upload = models.BigIntegerField(default=0)  # bytes
    lifetime_download = models.BigIntegerField(default=0)  # bytes
    invite_code_used = models.ForeignKey(
        InviteCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_banned = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True)
    banned_at = models.DateTimeField(null=True, blank=True)
    last_announce = models.DateTimeField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        help_text='User profile picture'
    )

    def __str__(self):
        return f"{self.username} ({self.user_class})"

    @property
    def available_credit(self):
        """اعتبار قابل استفاده"""
        return self.total_credit - self.locked_credit

    @property
    def ratio(self):
        """نسبت آپلود به دانلود"""
        if self.lifetime_download == 0:
            return 999.99 if self.lifetime_upload > 0 else 0.0
        return min(self.lifetime_upload / self.lifetime_download, 999.99)

    @property
    def download_multiplier(self):
        """ضریب دانلود بر اساس کلاس کاربر"""
        multipliers = {
            'newbie': 0.5,
            'member': 1.0,
            'trusted': 1.5,
            'elite': 2.0,
        }
        return multipliers.get(self.user_class, 1.0)

    @property
    def max_torrents(self):
        """حداکثر تعداد تورنت‌های مجاز"""
        limits = {
            'newbie': 1,
            'member': 5,
            'trusted': 15,
            'elite': 50,
        }
        return limits.get(self.user_class, 1)

    def can_download(self, torrent_size):
        """بررسی امکان دانلود تورنت"""
        if self.is_banned:
            return False, "User is banned"

        # بررسی اعتبار کافی
        required_credit = torrent_size / (1024 ** 3)  # GB
        if self.available_credit < required_credit:
            return False, "Insufficient credit"

        return True, "OK"

    class Meta:
        ordering = ['-date_joined']


class AuthToken(models.Model):
    """توکن‌های احراز هویت برای تراکر"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auth_tokens'
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    ip_bound = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Token for {self.user.username}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self, ip_address=None):
        if not self.is_active or self.is_expired():
            return False

        if self.ip_bound and ip_address and self.ip_bound != ip_address:
            return False

        return True

    class Meta:
        ordering = ['-created_at']
