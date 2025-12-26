from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
import secrets
import hashlib
import hmac
from .models import User, InviteCode, AuthToken


class InviteCodeSerializer(serializers.ModelSerializer):
    """Serializer برای کد دعوت"""

    class Meta:
        model = InviteCode
        fields = ['code', 'expires_at', 'is_active']
        read_only_fields = ['code', 'created_by']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer برای ثبت‌نام کاربر"""

    invite_code = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'invite_code', 'user_class', 'total_credit'
        ]
        read_only_fields = ['user_class', 'total_credit']

    def validate_invite_code(self, value):
        """بررسی اعتبار کد دعوت"""
        try:
            invite = InviteCode.objects.get(code=value)
            if not invite.is_active:
                raise serializers.ValidationError("کد دعوت غیرفعال است.")
            if invite.is_expired():
                raise serializers.ValidationError("کد دعوت منقضی شده است.")
            if invite.is_used():
                raise serializers.ValidationError("کد دعوت قبلاً استفاده شده است.")
            return invite
        except InviteCode.DoesNotExist:
            raise serializers.ValidationError("کد دعوت نامعتبر است.")

    def validate(self, data):
        """بررسی‌های کلی"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'رمز عبور و تکرار آن مطابقت ندارند.'
            })

        # بررسی نام کاربری منحصر به فرد
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({
                'username': 'این نام کاربری قبلاً استفاده شده است.'
            })

        # بررسی ایمیل منحصر به فرد
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({
                'email': 'این ایمیل قبلاً استفاده شده است.'
            })

        return data

    def create(self, validated_data):
        """ایجاد کاربر جدید"""
        invite_code = validated_data.pop('invite_code')
        validated_data.pop('password_confirm')

        # ایجاد کاربر
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # بروزرسانی کد دعوت
        invite_code.used_by = user
        invite_code.save()

        # تنظیم کد دعوت استفاده شده
        user.invite_code_used = invite_code
        user.save()

        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer برای لاگین"""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """احراز هویت کاربر"""
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if user.is_banned:
                    raise serializers.ValidationError({
                        'non_field_errors': ['حساب کاربری شما مسدود شده است.']
                    })
                data['user'] = user
            else:
                raise serializers.ValidationError({
                    'non_field_errors': ['نام کاربری یا رمز عبور اشتباه است.']
                })
        else:
            raise serializers.ValidationError({
                'non_field_errors': ['نام کاربری و رمز عبور الزامی هستند.']
            })

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer برای پروفایل کاربر"""

    ratio = serializers.SerializerMethodField()
    available_credit = serializers.SerializerMethodField()
    download_multiplier = serializers.SerializerMethodField()
    max_torrents = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'user_class', 'total_credit',
            'locked_credit', 'available_credit', 'lifetime_upload',
            'lifetime_download', 'ratio', 'download_multiplier',
            'max_torrents', 'is_banned', 'date_joined', 'last_login'
        ]
        read_only_fields = [
            'id', 'user_class', 'total_credit', 'locked_credit',
            'available_credit', 'lifetime_upload', 'lifetime_download',
            'ratio', 'download_multiplier', 'max_torrents',
            'is_banned', 'date_joined', 'last_login'
        ]

    def get_ratio(self, obj):
        return obj.ratio

    def get_available_credit(self, obj):
        return obj.available_credit

    def get_download_multiplier(self, obj):
        return obj.download_multiplier

    def get_max_torrents(self, obj):
        return obj.max_torrents


class UserStatsSerializer(serializers.ModelSerializer):
    """Serializer برای آمار کاربر"""

    ratio = serializers.SerializerMethodField()
    available_credit = serializers.SerializerMethodField()
    active_torrents = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'total_credit', 'locked_credit', 'available_credit',
            'lifetime_upload', 'lifetime_download', 'ratio',
            'user_class', 'active_torrents', 'last_announce'
        ]

    def get_ratio(self, obj):
        return obj.ratio

    def get_available_credit(self, obj):
        return obj.available_credit

    def get_active_torrents(self, obj):
        return obj.peers.filter(state__in=['started', 'completed']).count()


class AuthTokenSerializer(serializers.ModelSerializer):
    """Serializer برای توکن‌های احراز هویت"""

    class Meta:
        model = AuthToken
        fields = ['id', 'token', 'created_at', 'expires_at', 'is_active']
        read_only_fields = ['id', 'token', 'created_at', 'expires_at']


class AuthTokenCreateSerializer(serializers.ModelSerializer):
    """Serializer برای ایجاد توکن جدید"""

    class Meta:
        model = AuthToken
        fields = ['ip_bound']
        extra_kwargs = {
            'ip_bound': {'required': False, 'allow_null': True}
        }

    def create(self, validated_data):
        """ایجاد توکن HMAC جدید"""
        user = self.context['request'].user
        ip_bound = validated_data.get('ip_bound')

        # تولید توکن تصادفی
        token_value = secrets.token_hex(32)

        # تنظیم تاریخ انقضا (۱ هفته)
        expires_at = timezone.now() + timedelta(days=7)

        # ایجاد توکن
        token = AuthToken.objects.create(
            user=user,
            token=token_value,
            expires_at=expires_at,
            ip_bound=ip_bound
        )

        return token
