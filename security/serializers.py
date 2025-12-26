from rest_framework import serializers
from .models import SuspiciousActivity, AnnounceLog, IPBlock, RateLimit


class SuspiciousActivitySerializer(serializers.ModelSerializer):
    """Serializer برای فعالیت‌های مشکوک"""

    user_username = serializers.SerializerMethodField()
    torrent_name = serializers.SerializerMethodField()

    class Meta:
        model = SuspiciousActivity
        fields = [
            'id', 'user_username', 'activity_type', 'severity',
            'description', 'details', 'ip_address', 'torrent_name',
            'detected_at', 'is_resolved', 'resolved_at'
        ]

    def get_user_username(self, obj):
        return obj.user.username if obj.user else None

    def get_torrent_name(self, obj):
        return obj.torrent.name if obj.torrent else None


class AnnounceLogSerializer(serializers.ModelSerializer):
    """Serializer برای لاگ announce"""

    user_username = serializers.SerializerMethodField()
    torrent_name = serializers.SerializerMethodField()

    class Meta:
        model = AnnounceLog
        fields = [
            'id', 'user_username', 'torrent_name', 'event',
            'uploaded', 'downloaded', 'left', 'ip_address',
            'port', 'peer_id', 'timestamp', 'is_suspicious'
        ]

    def get_user_username(self, obj):
        return obj.user.username

    def get_torrent_name(self, obj):
        return obj.torrent.name


class IPBlockSerializer(serializers.ModelSerializer):
    """Serializer برای مسدودی IP"""

    blocked_by_username = serializers.SerializerMethodField()

    class Meta:
        model = IPBlock
        fields = [
            'id', 'ip_address', 'blocked_at', 'blocked_by_username',
            'reason', 'expires_at', 'is_active'
        ]

    def get_blocked_by_username(self, obj):
        return obj.blocked_by.username if obj.blocked_by else None


class RateLimitSerializer(serializers.ModelSerializer):
    """Serializer برای محدودیت نرخ"""

    class Meta:
        model = RateLimit
        fields = [
            'id', 'identifier', 'limit_type', 'count',
            'window_start', 'window_end'
        ]


class SecurityStatsSerializer(serializers.Serializer):
    """Serializer برای آمار امنیتی"""

    total_suspicious_activities = serializers.IntegerField()
    active_ip_blocks = serializers.IntegerField()
    recent_bans = serializers.IntegerField()
    top_suspicious_ips = serializers.ListField()
    security_alerts_today = serializers.IntegerField()


class SecurityReportSerializer(serializers.Serializer):
    """Serializer برای گزارش امنیتی"""

    report_type = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    data = serializers.DictField()
    generated_at = serializers.DateTimeField()
