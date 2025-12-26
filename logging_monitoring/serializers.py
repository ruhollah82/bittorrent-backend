from rest_framework import serializers
from .models import SystemLog, UserActivity, SystemStats, Alert


class SystemLogSerializer(serializers.ModelSerializer):
    """Serializer برای لاگ های سیستم"""

    user_username = serializers.SerializerMethodField()
    level_display = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()

    class Meta:
        model = SystemLog
        fields = [
            'id', 'level', 'level_display', 'category', 'category_display',
            'message', 'details', 'user_username', 'ip_address',
            'user_agent', 'timestamp'
        ]

    def get_user_username(self, obj):
        return obj.user.username if obj.user else None

    def get_level_display(self, obj):
        return dict(SystemLog.LOG_LEVELS).get(obj.level, obj.level)

    def get_category_display(self, obj):
        return dict(SystemLog.LOG_CATEGORIES).get(obj.category, obj.category)


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer برای فعالیت های کاربران"""

    user_username = serializers.SerializerMethodField()
    activity_display = serializers.SerializerMethodField()

    class Meta:
        model = UserActivity
        fields = [
            'id', 'user_username', 'activity_type', 'activity_display',
            'description', 'details', 'ip_address', 'user_agent', 'timestamp'
        ]

    def get_user_username(self, obj):
        return obj.user.username

    def get_activity_display(self, obj):
        return dict(UserActivity.ACTIVITY_TYPES).get(obj.activity_type, obj.activity_type)


class SystemStatsSerializer(serializers.ModelSerializer):
    """Serializer برای آمار سیستم"""

    class Meta:
        model = SystemStats
        fields = [
            'date', 'total_users', 'active_users', 'total_torrents',
            'active_torrents', 'total_peers', 'total_upload',
            'total_download', 'total_credit_transacted',
            'suspicious_activities', 'blocked_ips'
        ]


class AlertSerializer(serializers.ModelSerializer):
    """Serializer برای هشدارها"""

    user_username = serializers.SerializerMethodField()
    torrent_name = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    alert_type_display = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'alert_type_display', 'priority',
            'priority_display', 'title', 'message', 'details',
            'user_username', 'torrent_name', 'created_at',
            'is_acknowledged', 'acknowledged_at'
        ]

    def get_user_username(self, obj):
        return obj.user.username if obj.user else None

    def get_torrent_name(self, obj):
        return obj.torrent.name if obj.torrent else None

    def get_priority_display(self, obj):
        return dict(Alert.PRIORITY_LEVELS).get(obj.priority, obj.priority)

    def get_alert_type_display(self, obj):
        return dict(Alert.ALERT_TYPES).get(obj.alert_type, obj.alert_type)


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer برای آمار داشبورد"""

    # آمار کاربران
    total_users = serializers.IntegerField()
    active_users_24h = serializers.IntegerField()
    new_users_7d = serializers.IntegerField()

    # آمار تورنت
    total_torrents = serializers.IntegerField()
    active_torrents = serializers.IntegerField()

    # آمار credit
    total_credit_transacted = serializers.DecimalField(max_digits=15, decimal_places=2)

    # آمار امنیتی
    suspicious_activities_24h = serializers.IntegerField()
    active_ip_blocks = serializers.IntegerField()
    alerts_unacknowledged = serializers.IntegerField()

    # آمار سیستم
    system_logs_24h = serializers.IntegerField()
    announce_logs_24h = serializers.IntegerField()

    # روندها
    user_growth_trend = serializers.ListField()
    credit_trend = serializers.ListField()
    activity_trend = serializers.ListField()


class LogAnalysisSerializer(serializers.Serializer):
    """Serializer برای تحلیل لاگ ها"""

    analysis_type = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    filters = serializers.DictField()
    results = serializers.DictField()
    insights = serializers.ListField()
    generated_at = serializers.DateTimeField()
