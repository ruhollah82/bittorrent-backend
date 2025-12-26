from rest_framework import serializers
from .models import CreditTransaction, UserCredit


class CreditTransactionSerializer(serializers.ModelSerializer):
    """Serializer برای تراکنش‌های credit"""

    torrent_name = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()

    class Meta:
        model = CreditTransaction
        fields = [
            'id', 'user_username', 'torrent_name', 'transaction_type',
            'amount', 'description', 'status', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']

    def get_torrent_name(self, obj):
        return obj.torrent.name if obj.torrent else None

    def get_user_username(self, obj):
        return obj.user.username


class CreditBalanceSerializer(serializers.Serializer):
    """Serializer برای نمایش موجودی credit"""

    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    locked_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    available_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    lifetime_upload = serializers.IntegerField()
    lifetime_download = serializers.IntegerField()
    ratio = serializers.FloatField()
    user_class = serializers.CharField()
    download_multiplier = serializers.FloatField()
    max_torrents = serializers.IntegerField()


class CreditAdjustmentSerializer(serializers.Serializer):
    """Serializer برای تنظیم credit توسط ادمین"""

    user_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(max_length=500)
    transaction_type = serializers.ChoiceField(
        choices=[
            ('bonus', 'Bonus'),
            ('penalty', 'Penalty'),
            ('admin_adjust', 'Admin Adjustment'),
        ],
        default='admin_adjust'
    )


class UserClassInfoSerializer(serializers.Serializer):
    """Serializer برای نمایش اطلاعات کلاس‌های کاربری"""

    user_class = serializers.CharField()
    requirements = serializers.DictField()
    benefits = serializers.DictField()
    restrictions = serializers.DictField()
