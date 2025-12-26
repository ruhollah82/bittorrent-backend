from rest_framework import serializers
from .models import Torrent, TorrentStats, Peer


class TorrentSerializer(serializers.ModelSerializer):
    """Serializer برای لیست تورنت‌ها"""

    created_by_username = serializers.SerializerMethodField()
    size_formatted = serializers.SerializerMethodField()
    age_days = serializers.SerializerMethodField()

    class Meta:
        model = Torrent
        fields = [
            'id', 'info_hash', 'name', 'size', 'size_formatted',
            'files_count', 'created_by_username', 'created_at',
            'category', 'is_private', 'age_days'
        ]

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else 'Anonymous'

    def get_size_formatted(self, obj):
        return obj.size_gb

    def get_age_days(self, obj):
        from django.utils import timezone
        return (timezone.now() - obj.created_at).days


class TorrentDetailSerializer(serializers.ModelSerializer):
    """Serializer برای جزئیات تورنت"""

    created_by_username = serializers.SerializerMethodField()
    size_formatted = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    health = serializers.SerializerMethodField()

    class Meta:
        model = Torrent
        fields = [
            'id', 'info_hash', 'name', 'description', 'size',
            'size_formatted', 'files_count', 'created_by_username',
            'created_at', 'updated_at', 'category', 'tags',
            'is_private', 'stats', 'health'
        ]

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else 'Anonymous'

    def get_size_formatted(self, obj):
        return obj.size_gb

    def get_stats(self, obj):
        try:
            stats = obj.stats
            return {
                'seeders': stats.seeders,
                'leechers': stats.leechers,
                'completed': stats.completed,
                'total_uploaded': stats.total_uploaded,
                'total_downloaded': stats.total_downloaded,
            }
        except TorrentStats.DoesNotExist:
            return {
                'seeders': 0,
                'leechers': 0,
                'completed': 0,
                'total_uploaded': 0,
                'total_downloaded': 0,
            }

    def get_health(self, obj):
        try:
            stats = obj.stats
            seeders = stats.seeders
            leechers = stats.leechers
            total_peers = seeders + leechers

            if total_peers == 0:
                return {'score': 0, 'status': 'dead'}
            elif seeders >= leechers:
                score = min(100, (seeders / max(1, leechers)) * 50)
                status = 'excellent' if score >= 80 else 'good'
            else:
                score = max(0, 50 - (leechers / max(1, seeders)) * 25)
                status = 'poor' if score < 30 else 'fair'

            return {'score': round(score, 1), 'status': status}
        except TorrentStats.DoesNotExist:
            return {'score': 0, 'status': 'dead'}


class TorrentStatsSerializer(serializers.ModelSerializer):
    """Serializer برای آمار تورنت"""

    torrent_name = serializers.SerializerMethodField()

    class Meta:
        model = TorrentStats
        fields = [
            'torrent_name', 'seeders', 'leechers', 'completed',
            'total_uploaded', 'total_downloaded', 'last_updated'
        ]

    def get_torrent_name(self, obj):
        return obj.torrent.name


class PeerSerializer(serializers.ModelSerializer):
    """Serializer برای peerها"""

    user_username = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    download_speed = serializers.SerializerMethodField()
    upload_speed = serializers.SerializerMethodField()

    class Meta:
        model = Peer
        fields = [
            'id', 'user_username', 'peer_id', 'ip_address', 'port',
            'uploaded', 'downloaded', 'left', 'progress',
            'is_seeder', 'download_speed', 'upload_speed',
            'first_announced', 'last_announced', 'user_agent'
        ]

    def get_user_username(self, obj):
        return obj.user.username

    def get_progress(self, obj):
        return obj.progress

    def get_download_speed(self, obj):
        # TODO: Calculate actual speeds from announce intervals
        return 0

    def get_upload_speed(self, obj):
        # TODO: Calculate actual speeds from announce intervals
        return 0


class TorrentUploadSerializer(serializers.Serializer):
    """Serializer برای آپلود تورنت"""

    torrent_file = serializers.FileField()
    category = serializers.CharField(max_length=50, required=False)
    description = serializers.CharField(required=False)
    is_private = serializers.BooleanField(default=True)

    def validate_torrent_file(self, value):
        # بررسی اندازه فایل (حداکثر ۱۰MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Torrent file too large (max 10MB)")

        # بررسی نوع فایل
        if not value.name.lower().endswith('.torrent'):
            raise serializers.ValidationError("File must be a .torrent file")

        return value
