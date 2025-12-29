from django.db import models
from django.conf import settings
from django.utils import timezone
import hashlib


class Category(models.Model):
    """مدل دسته‌بندی تورنت"""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # Icon name/class
    color = models.CharField(max_length=7, blank=True)  # Hex color code
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


class Torrent(models.Model):
    """مدل تورنت"""

    info_hash = models.CharField(max_length=40, unique=True)  # SHA1 hash
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    size = models.BigIntegerField()  # bytes
    files_count = models.IntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_torrents'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_private = models.BooleanField(default=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='torrents'
    )
    tags = models.JSONField(default=list, blank=True)  # لیست تگ‌ها

    # Metadata
    piece_length = models.IntegerField(null=True, blank=True)
    pieces_hash = models.TextField(blank=True)  # concatenated piece hashes
    announce_url = models.URLField(blank=True)
    comment = models.TextField(blank=True)
    created_by_client = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name} ({self.info_hash[:8]})"

    @property
    def size_gb(self):
        """سایز به گیگابایت"""
        return self.size / (1024 ** 3)

    @property
    def info_hash_display(self):
        """نمایش هش به صورت خوانا"""
        return self.info_hash.upper()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['info_hash']),
            models.Index(fields=['created_by']),
            models.Index(fields=['is_active']),
            models.Index(fields=['category']),
        ]


class TorrentStats(models.Model):
    """آمار تورنت"""

    torrent = models.OneToOneField(
        Torrent,
        on_delete=models.CASCADE,
        related_name='stats'
    )
    seeders = models.IntegerField(default=0)
    leechers = models.IntegerField(default=0)
    completed = models.IntegerField(default=0)  # تعداد کامل کننده‌ها
    total_uploaded = models.BigIntegerField(default=0)  # کل آپلود شده
    total_downloaded = models.BigIntegerField(default=0)  # کل دانلود شده
    last_updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Stats for {self.torrent.name}"

    @property
    def total_peers(self):
        return self.seeders + self.leechers

    class Meta:
        indexes = [
            models.Index(fields=['torrent']),
            models.Index(fields=['-last_updated']),
        ]


class Peer(models.Model):
    """مدل peerها"""

    PEER_STATES = [
        ('started', 'Started'),
        ('stopped', 'Stopped'),
        ('completed', 'Completed'),
    ]

    torrent = models.ForeignKey(
        Torrent,
        on_delete=models.CASCADE,
        related_name='peers'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='peers',
        null=True,
        blank=True
    )
    peer_id = models.CharField(max_length=40)  # 20 bytes hex encoded
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField()
    uploaded = models.BigIntegerField(default=0)
    downloaded = models.BigIntegerField(default=0)
    left = models.BigIntegerField()  # bytes remaining
    state = models.CharField(
        max_length=10,
        choices=PEER_STATES,
        default='started'
    )
    is_seeder = models.BooleanField(default=False)
    first_announced = models.DateTimeField(default=timezone.now)
    last_announced = models.DateTimeField(default=timezone.now)
    user_agent = models.CharField(max_length=200, blank=True)

    def __str__(self):
        username = self.user.username if self.user else f"anonymous ({self.peer_id[:8]}...)"
        return f"Peer {username} on {self.torrent.name}"

    @property
    def progress(self):
        """پیشرفت دانلود (0-100)"""
        if self.torrent.size == 0:
            return 100
        return ((self.torrent.size - self.left) / self.torrent.size) * 100

    class Meta:
        unique_together = ['torrent', 'user']
        ordering = ['-last_announced']
        indexes = [
            models.Index(fields=['torrent', 'last_announced']),
            models.Index(fields=['user']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['is_seeder']),
        ]
