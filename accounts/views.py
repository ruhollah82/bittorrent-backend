from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
import secrets
import hashlib
import hmac
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from .models import User, InviteCode, AuthToken
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    UserProfileSerializer, UserStatsSerializer,
    AuthTokenSerializer, AuthTokenCreateSerializer,
    InviteCodeSerializer
)
from logging_monitoring.models import UserActivity, SystemLog


@extend_schema(
    tags=['Authentication'],
    summary='User Registration',
    description='Register a new user account with invite code validation.',
    request=UserRegistrationSerializer,
    responses={
        201: UserProfileSerializer,
        400: OpenApiExample(
            'Validation Error',
            value={
                'username': ['A user with that username already exists.'],
                'invite_code': ['کد دعوت نامعتبر است.']
            }
        )
    },
    examples=[
        OpenApiExample(
            'Successful Registration',
            request_only=True,
            value={
                'username': 'johndoe',
                'email': 'john@example.com',
                'password': 'securepassword123',
                'password_confirm': 'securepassword123',
                'invite_code': 'ABC123DEF'
            }
        )
    ]
)
class RegisterView(APIView):
    """User registration with invite code validation"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # لاگ فعالیت
            UserActivity.objects.create(
                user=user,
                activity_type='register',
                description='ثبت‌نام کاربر جدید',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            # لاگ سیستم
            SystemLog.objects.create(
                category='auth',
                level='info',
                message=f'کاربر جدید ثبت‌نام کرد: {user.username}',
                details={'user_id': user.id, 'invite_used': user.invite_code_used.code if user.invite_code_used else None},
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            return Response({
                'message': 'کاربر با موفقیت ایجاد شد.',
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """دریافت IP آدرس کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema(
    tags=['Authentication'],
    summary='User Login',
    description='Authenticate user and return JWT tokens.',
    request=UserLoginSerializer,
    responses={
        200: OpenApiExample(
            'Login Success',
            value={
                'message': 'ورود با موفقیت انجام شد.',
                'tokens': {
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                },
                'user': {
                    'id': 1,
                    'username': 'johndoe',
                    'email': 'john@example.com'
                }
            }
        ),
        400: OpenApiExample(
            'Login Failed',
            value={
                'non_field_errors': ['نام کاربری یا رمز عبور اشتباه است.']
            }
        )
    },
    examples=[
        OpenApiExample(
            'Login Request',
            request_only=True,
            value={
                'username': 'johndoe',
                'password': 'securepassword123'
            }
        )
    ]
)
class LoginView(APIView):
    """User authentication with JWT token generation"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # ایجاد JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            # بروزرسانی last_login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            # لاگ فعالیت
            UserActivity.objects.create(
                user=user,
                activity_type='login',
                description='ورود به سیستم',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            return Response({
                'message': 'ورود با موفقیت انجام شد.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': access_token,
                },
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """دریافت IP آدرس کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CustomTokenRefreshView(TokenRefreshView):
    """نمای سفارشی refresh token"""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # لاگ refresh token
            try:
                # از token می‌توان user را استخراج کرد
                from rest_framework_simplejwt.tokens import AccessToken
                access_token = AccessToken(response.data['access'])
                user_id = access_token['user_id']
                user = User.objects.get(id=user_id)

                UserActivity.objects.create(
                    user=user,
                    activity_type='login',
                    description='refresh token',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except:
                pass

        return response

    def get_client_ip(self, request):
        """دریافت IP آدرس کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema(
    tags=['User Management'],
    summary='User Profile',
    description='Get and update authenticated user profile information.',
    responses={
        200: UserProfileSerializer,
        401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'})
    }
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile management - get and update profile"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        old_data = {
            'email': instance.email,
            'username': instance.username
        }

        self.perform_update(serializer)

        # لاگ تغییرات
        changes = []
        if old_data['email'] != instance.email:
            changes.append(f'email: {old_data["email"]} -> {instance.email}')
        if old_data['username'] != instance.username:
            changes.append(f'username: {old_data["username"]} -> {instance.username}')

        if changes:
            UserActivity.objects.create(
                user=instance,
                activity_type='profile_update',
                description=f'بروزرسانی پروفایل: {", ".join(changes)}',
                details={'changes': changes},
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

        return Response(serializer.data)

    def get_client_ip(self, request):
        """دریافت IP آدرس کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserStatsView(generics.RetrieveAPIView):
    """نمای آمار کاربر"""

    serializer_class = UserStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AuthTokenListView(generics.ListCreateAPIView):
    """نمای لیست و ایجاد توکن‌های احراز هویت"""

    serializer_class = AuthTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AuthToken.objects.filter(user=self.request.user, is_active=True)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AuthTokenCreateSerializer
        return AuthTokenSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # لاگ ایجاد توکن
        UserActivity.objects.create(
            user=request.user,
            activity_type='profile_update',
            description='ایجاد توکن احراز هویت جدید',
            details={'token_id': instance.id},
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # استفاده از AuthTokenSerializer برای پاسخ
        response_serializer = AuthTokenSerializer(instance)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_client_ip(self, request):
        """دریافت IP آدرس کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuthTokenDetailView(generics.RetrieveDestroyAPIView):
    """نمای جزئیات و حذف توکن"""

    serializer_class = AuthTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AuthToken.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        # لاگ حذف توکن
        UserActivity.objects.create(
            user=self.request.user,
            activity_type='profile_update',
            description='حذف توکن احراز هویت',
            details={'token_id': instance.id},
            ip_address=self.get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        instance.is_active = False
        instance.save()

    def get_client_ip(self, request):
        """دریافت IP آدرس کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def create_invite_code(request):
    """ایجاد کد دعوت جدید (فقط برای ادمین‌ها)"""

    if not request.user.is_staff:
        return Response(
            {'error': 'دسترسی غیرمجاز'},
            status=status.HTTP_403_FORBIDDEN
        )

    expires_at = request.data.get('expires_at')
    if expires_at:
        expires_at = timezone.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    else:
        expires_at = timezone.now() + timedelta(days=30)

    invite = InviteCode.objects.create(
        created_by=request.user,
        expires_at=expires_at
    )

    serializer = InviteCodeSerializer(invite)
    return Response(serializer.data, status=status.HTTP_201_CREATED)