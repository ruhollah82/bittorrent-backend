from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from decimal import Decimal

from .models import InviteCode, AuthToken

User = get_user_model()


class AccountsAPITestCase(APITestCase):
    """Comprehensive API tests for accounts app"""

    def setUp(self):
        """Set up test data"""
        # Use direct URL paths since the API includes these at /api/auth/ and /api/user/
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.profile_url = '/api/user/profile/'
        self.token_list_url = '/api/user/tokens/'
        self.invite_create_url = '/api/auth/invite/create/'

        # Create test invite code
        self.invite_code = InviteCode.objects.create(
            code='TESTCODE123',
            created_by=None,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.invite_code_used = self.invite_code
        self.user.save()

    def test_user_registration_successful(self):
        """Test successful user registration with valid invite code"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'invite_code': 'TESTCODE123'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('message', response.data)

        # Verify user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.invite_code_used, self.invite_code)

        # Verify invite code was marked as used
        self.invite_code.refresh_from_db()
        self.assertEqual(self.invite_code.used_by, user)

    def test_user_registration_without_invite_code(self):
        """Test user registration fails without invite code"""
        data = {
            'username': 'newuser2',
            'email': 'newuser2@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invite_code', response.data)

    def test_user_registration_invalid_invite_code(self):
        """Test user registration fails with invalid invite code"""
        data = {
            'username': 'newuser3',
            'email': 'newuser3@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'invite_code': 'INVALIDCODE'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invite_code', response.data)

    def test_user_registration_duplicate_username(self):
        """Test user registration fails with duplicate username"""
        data = {
            'username': 'testuser',  # Already exists
            'email': 'different@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'invite_code': 'TESTCODE123'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_user_registration_duplicate_email(self):
        """Test user registration fails with duplicate email"""
        data = {
            'username': 'newuser4',
            'email': 'test@example.com',  # Already exists
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'invite_code': 'TESTCODE123'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_user_registration_weak_password(self):
        """Test user registration fails with weak password"""
        data = {
            'username': 'newuser5',
            'email': 'newuser5@example.com',
            'password': '123',  # Too short
            'password_confirm': '123',
            'invite_code': 'TESTCODE123'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_user_login_successful(self):
        """Test successful user login"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('message', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

    def test_user_login_wrong_credentials(self):
        """Test login fails with wrong credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }

        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_nonexistent_user(self):
        """Test login fails with nonexistent user"""
        data = {
            'username': 'nonexistent',
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_user_profile_authenticated(self):
        """Test getting user profile when authenticated"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_get_user_profile_unauthenticated(self):
        """Test getting user profile fails when unauthenticated"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_profile(self):
        """Test getting user profile"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertIn('ratio', response.data)
        self.assertIn('available_credit', response.data)


    def test_token_list_authenticated(self):
        """Test listing auth tokens when authenticated"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.token_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)  # Paginated response





    def test_invite_code_expiration(self):
        """Test expired invite code cannot be used"""
        # Create expired invite code
        expired_code = InviteCode.objects.create(
            code='EXPIRED123',
            expires_at=timezone.now() - timedelta(days=1)  # Already expired
        )

        data = {
            'username': 'newuser6',
            'email': 'newuser6@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'invite_code': 'EXPIRED123'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invite_code', response.data)

    def test_invite_code_already_used(self):
        """Test already used invite code cannot be used again"""
        # Mark invite code as used
        self.invite_code.used_by = self.user
        self.invite_code.save()

        data = {
            'username': 'newuser7',
            'email': 'newuser7@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'invite_code': 'TESTCODE123'
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invite_code', response.data)

    def test_user_generate_invite_success(self):
        """Test successful invite code generation by regular user"""
        # Set up user with member class and sufficient credits
        self.user.user_class = 'member'
        self.user.total_credit = Decimal('10.00')
        self.user.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/auth/invite/generate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertIn('code', data)
        self.assertIn('expires_at', data)
        self.assertTrue(data['is_active'])

        # Verify invite was created
        invite = InviteCode.objects.get(code=data['code'])
        self.assertEqual(invite.created_by, self.user)

        # Verify credits were deducted (1 credit cost)
        self.user.refresh_from_db()
        self.assertEqual(self.user.available_credit, Decimal('9.00'))

    def test_user_generate_invite_insufficient_class(self):
        """Test invite generation fails for newbie users"""
        # User remains newbie (default)
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/auth/invite/generate/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.data
        self.assertIn('error', data)
        self.assertIn('current_class', data)
        self.assertEqual(data['current_class'], 'newbie')

    def test_user_generate_invite_insufficient_credits(self):
        """Test invite generation fails with insufficient credits"""
        self.user.user_class = 'member'
        self.user.total_credit = Decimal('0.50')  # Less than required 1.00
        self.user.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/auth/invite/generate/')
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        data = response.data
        self.assertIn('error', data)
        self.assertIn('required_credit', data)
        self.assertIn('available_credit', data)
        self.assertEqual(Decimal(data['required_credit']), Decimal('1.00'))

    def test_user_generate_invite_daily_limit(self):
        """Test invite generation fails when daily limit is exceeded"""
        from django.utils import timezone
        from datetime import timedelta

        self.user.user_class = 'member'
        self.user.total_credit = Decimal('50.00')
        self.user.save()

        # Create 2 invites for today (the limit)
        today = timezone.now()
        for i in range(2):
            InviteCode.objects.create(
                created_by=self.user,
                expires_at=today + timedelta(days=7)
            )

        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/auth/invite/generate/')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        data = response.data
        self.assertIn('error', data)
        self.assertIn('used_today', data)
        self.assertEqual(data['used_today'], 2)
        self.assertEqual(data['limit'], 2)

    def test_user_invite_codes_list(self):
        """Test listing user's created invite codes"""
        # Create some invite codes for the user
        from accounts.models import InviteCode
        from django.utils import timezone
        from datetime import timedelta

        self.user.user_class = 'member'
        self.user.total_credit = Decimal('50.00')
        self.user.save()

        # Create a used invite code
        used_invite = InviteCode.objects.create(
            created_by=self.user,
            used_by=self.user,  # Self-used for testing
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Create an unused invite code
        unused_invite = InviteCode.objects.create(
            created_by=self.user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/auth/invite/my-codes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('stats', data)
        self.assertIn('invite_codes', data)

        # Check stats
        stats = data['stats']
        self.assertEqual(stats['total_created'], 2)
        self.assertEqual(stats['total_used'], 1)
        self.assertEqual(stats['total_active'], 1)

        # Check invite codes
        invite_codes = data['invite_codes']
        self.assertEqual(len(invite_codes), 2)

        # Find the used invite
        used_invite_data = next(code for code in invite_codes if code['code'] == used_invite.code)
        self.assertEqual(used_invite_data['used_by_username'], self.user.username)
        self.assertEqual(used_invite_data['status'], 'used')

        # Find the unused invite
        unused_invite_data = next(code for code in invite_codes if code['code'] == unused_invite.code)
        self.assertIsNone(unused_invite_data['used_by_username'])
        self.assertEqual(unused_invite_data['status'], 'active')
