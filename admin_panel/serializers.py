from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import User, InviteCode, AuthToken
from credits.models import CreditTransaction
from security.models import SuspiciousActivity, IPBlock
from logging_monitoring.models import Alert, SystemLog
from .models import AdminAction, SystemConfig

User = get_user_model()


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer برای مدیریت کاربران در پنل ادمین"""

    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    lifetime_upload = serializers.IntegerField(read_only=True)
    lifetime_download = serializers.IntegerField(read_only=True)
    ratio = serializers.FloatField(read_only=True)
    active_peers = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    account_age_days = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'user_class', 'total_credit',
            'lifetime_upload', 'lifetime_download', 'ratio',
            'is_banned', 'ban_reason', 'date_joined', 'last_login',
            'active_peers', 'last_activity', 'account_age_days'
        ]
        read_only_fields = [
            'id', 'total_credit', 'lifetime_upload', 'lifetime_download',
            'ratio', 'date_joined', 'last_login', 'active_peers',
            'last_activity', 'account_age_days'
        ]

    def get_active_peers(self, obj):
        return obj.peers.filter(state__in=['started', 'completed']).count()

    def get_last_activity(self, obj):
        return obj.last_login or obj.date_joined

    def get_account_age_days(self, obj):
        from django.utils import timezone
        return (timezone.now() - obj.date_joined).days


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer برای بروزرسانی کاربران"""

    class Meta:
        model = User
        fields = ['user_class', 'is_banned', 'ban_reason']

    def validate_user_class(self, value):
        valid_classes = [choice[0] for choice in User.USER_CLASSES]
        if value not in valid_classes:
            raise serializers.ValidationError(f"Invalid user class. Valid choices: {valid_classes}")
        return value


class InviteCodeManagementSerializer(serializers.ModelSerializer):
    """Serializer برای مدیریت کدهای دعوت"""

    used_by_username = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = InviteCode
        fields = [
            'id', 'code', 'created_by_username', 'used_by_username',
            'expires_at', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'code', 'created_at']

    def get_used_by_username(self, obj):
        return obj.used_by.username if obj.used_by else None

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else None


class BulkInviteCodeSerializer(serializers.Serializer):
    """Serializer برای ایجاد کدهای دعوت انبوه"""

    count = serializers.IntegerField(min_value=1, max_value=100, default=10)
    expires_days = serializers.IntegerField(min_value=1, max_value=365, required=False)

    def create(self, validated_data):
        from django.utils import timezone
        from datetime import timedelta

        count = validated_data['count']
        expires_days = validated_data.get('expires_days')

        expires_at = None
        if expires_days:
            expires_at = timezone.now() + timedelta(days=expires_days)

        codes = []
        for _ in range(count):
            invite = InviteCode.objects.create(
                created_by=self.context['request'].user,
                expires_at=expires_at
            )
            codes.append(invite.code)

        return {'created_codes': codes, 'expires_at': expires_at}


class SystemConfigSerializer(serializers.ModelSerializer):
    """Serializer برای تنظیمات سیستم"""

    updated_by_username = serializers.SerializerMethodField()

    class Meta:
        model = SystemConfig
        fields = [
            'id', 'key', 'value', 'config_type', 'description',
            'is_active', 'created_at', 'updated_at', 'updated_by_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'updated_by_username']

    def get_updated_by_username(self, obj):
        return obj.updated_by.username if obj.updated_by else None


class AdminDashboardSerializer(serializers.Serializer):
    """Serializer برای داشبورد ادمین"""

    # آمار کلی
    total_users = serializers.IntegerField()
    total_torrents = serializers.IntegerField()
    total_credit_transacted = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_peers = serializers.IntegerField()

    # آمار امنیتی
    suspicious_activities_today = serializers.IntegerField()
    active_ip_blocks = serializers.IntegerField()
    banned_users = serializers.IntegerField()

    # آمار سیستم
    system_alerts = serializers.IntegerField()
    recent_logs = serializers.IntegerField()

    # لیست کاربران اخیر
    recent_users = serializers.ListField()
    # لیست فعالیت‌های مشکوک اخیر
    recent_suspicious = serializers.ListField()
    # لیست هشدارها
    recent_alerts = serializers.ListField()


class AdminReportSerializer(serializers.Serializer):
    """Serializer برای گزارش‌های ادمین"""

    report_type = serializers.ChoiceField(
        choices=[
            ('user_activity', 'User Activity Report'),
            ('security_summary', 'Security Summary'),
            ('credit_usage', 'Credit Usage Report'),
            ('system_performance', 'System Performance'),
        ]
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    filters = serializers.DictField(required=False)

    # نتایج گزارش
    summary = serializers.DictField(read_only=True)
    data = serializers.ListField(read_only=True)
    charts = serializers.DictField(read_only=True)


class AdminActionSerializer(serializers.ModelSerializer):
    """Serializer برای اقدامات ادمین"""

    admin_username = serializers.SerializerMethodField()
    target_user_username = serializers.SerializerMethodField()

    class Meta:
        model = AdminAction
        fields = [
            'id', 'admin_username', 'action_type', 'target_user_username',
            'description', 'details', 'ip_address', 'timestamp'
        ]

    def get_admin_username(self, obj):
        return obj.admin.username

    def get_target_user_username(self, obj):
        return obj.target_user.username if obj.target_user else None


class TorrentModerationSerializer(serializers.Serializer):
    """Serializer برای moderation تورنت‌ها"""

    # TODO: implement when torrents app is complete
    torrent_id = serializers.IntegerField()
    action = serializers.ChoiceField(
        choices=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('delete', 'Delete'),
            ('feature', 'Feature'),
        ]
    )
    reason = serializers.CharField(required=False)


class MassUserActionSerializer(serializers.Serializer):
    """Serializer برای اقدامات انبوه روی کاربران"""

    user_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(
        choices=[
            ('ban', 'Ban Users'),
            ('unban', 'Unban Users'),
            ('change_class', 'Change Class'),
            ('reset_ratio', 'Reset Ratio'),
        ]
    )
    reason = serializers.CharField(required=False)
    new_class = serializers.ChoiceField(
        choices=[choice[0] for choice in User.USER_CLASSES],
        required=False
    )

    def validate(self, data):
        if data['action'] == 'change_class' and not data.get('new_class'):
            raise serializers.ValidationError("new_class is required for change_class action")
        return data
