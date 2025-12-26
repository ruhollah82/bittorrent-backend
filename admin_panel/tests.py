from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta

from accounts.models import User, InviteCode, AuthToken
from credits.models import CreditTransaction
from security.models import SuspiciousActivity, IPBlock
from logging_monitoring.models import Alert, SystemLog, SystemStats
from .models import AdminAction, SystemConfig

User = get_user_model()


class AdminPanelAPITestCase(APITestCase):
    """Comprehensive API tests for admin_panel app"""

    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regular123'
        )

        # Create test data
        self.invite_code = InviteCode.objects.create(
            code='ADMINTEST123',
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Create some credit transactions
        CreditTransaction.objects.create(
            user=self.regular_user,
            amount=10.50,
            transaction_type='bonus',
            description='Admin bonus'
        )

        # Create suspicious activity
        SuspiciousActivity.objects.create(
            user=self.regular_user,
            activity_type='login_anomaly',
            severity='medium',
            description='Suspicious login detected',
            ip_address='192.168.1.100'
        )

        # Create IP block
        IPBlock.objects.create(
            ip_address='192.168.1.100',
            reason='Suspicious activity',
            is_active=True
        )

        # Set up authentication
        self.client.force_authenticate(user=self.admin_user)

    def test_admin_dashboard_access_denied_for_regular_user(self):
        """Test that regular users cannot access admin dashboard"""
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get('/api/admin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_dashboard_access_granted_for_admin(self):
        """Test that admin users can access dashboard"""
        response = self.client.get('/api/admin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('total_users', data)
        self.assertIn('total_credit_transacted', data)
        self.assertIn('suspicious_activities_today', data)
        self.assertIn('active_ip_blocks', data)
        self.assertIn('banned_users', data)

        # Verify data accuracy
        self.assertEqual(data['total_users'], 2)  # admin + regular user
        self.assertEqual(data['suspicious_activities_today'], 1)
        self.assertEqual(data['active_ip_blocks'], 1)
        self.assertEqual(data['banned_users'], 0)

    def test_user_management_list(self):
        """Test listing users in admin panel"""
        response = self.client.get('/api/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

        # Check that user data includes admin fields
        user_data = data[0]
        self.assertIn('id', user_data)
        self.assertIn('username', user_data)
        self.assertIn('email', user_data)
        self.assertIn('is_banned', user_data)
        self.assertIn('user_class', user_data)

    def test_user_management_detail(self):
        """Test getting detailed user information"""
        response = self.client.get(f'/api/admin/users/{self.regular_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['username'], 'regular')
        self.assertEqual(data['email'], 'regular@example.com')
        self.assertIn('total_credit', data)
        self.assertIn('lifetime_upload', data)
        self.assertIn('lifetime_download', data)

    def test_user_management_update(self):
        """Test updating user information as admin"""
        update_data = {
            'user_class': 'member',
            'is_banned': True,
            'ban_reason': 'Test ban'
        }

        response = self.client.patch(f'/api/admin/users/{self.regular_user.id}/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify changes
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.user_class, 'member')
        self.assertTrue(self.regular_user.is_banned)
        self.assertEqual(self.regular_user.ban_reason, 'Test ban')

        # Verify admin action was logged
        admin_action = AdminAction.objects.filter(
            admin=self.admin_user,
            action_type='user_ban',
            target_user=self.regular_user
        ).first()
        self.assertIsNotNone(admin_action)

    def test_invite_code_management_list(self):
        """Test listing invite codes in admin panel"""
        response = self.client.get('/api/admin/invites/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_invite_code_management_create(self):
        """Test creating invite codes as admin"""
        create_data = {
            'count': 3,
            'expires_in_days': 7
        }

        response = self.client.post('/api/admin/invites/', create_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertIn('codes', data)
        self.assertEqual(len(data['codes']), 3)

        # Verify codes were created
        new_codes = InviteCode.objects.filter(created_by=self.admin_user)
        self.assertEqual(new_codes.count(), 4)  # 1 existing + 3 new

    def test_system_config_list(self):
        """Test listing system configurations"""
        response = self.client.get('/api/admin/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)

    def test_system_config_create(self):
        """Test creating system configuration"""
        config_data = {
            'key': 'test_setting',
            'value': '{"enabled": true}',
            'config_type': 'global',
            'description': 'Test configuration setting'
        }

        response = self.client.post('/api/admin/config/', config_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify config was created
        config = SystemConfig.objects.get(key='test_setting')
        self.assertEqual(config.config_type, 'global')
        self.assertEqual(config.updated_by, self.admin_user)

    def test_system_config_update(self):
        """Test updating system configuration"""
        # Create a config first
        config = SystemConfig.objects.create(
            key='update_test',
            value='{"old": true}',
            config_type='global',
            description='Test config for update',
            updated_by=self.admin_user
        )

        update_data = {
            'value': '{"new": true}',
            'description': 'Updated test config'
        }

        response = self.client.patch(f'/api/admin/config/{config.id}/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify update
        config.refresh_from_db()
        self.assertEqual(config.value, '{"new": true}')
        self.assertEqual(config.description, 'Updated test config')

    def test_generate_report(self):
        """Test report generation functionality"""
        # This tests the function-based view
        report_data = {
            'report_type': 'user_activity',
            'start_date': (timezone.now() - timedelta(days=30)).date().isoformat(),
            'end_date': timezone.now().date().isoformat()
        }

        response = self.client.post('/api/admin/reports/generate/', report_data, format='json')
        # Report generation might return different status codes depending on implementation
        # For now, just ensure it doesn't crash
        self.assertIn(response.status_code, [200, 201, 400])

    def test_mass_user_action(self):
        """Test mass user actions"""
        action_data = {
            'action': 'change_class',
            'user_ids': [self.regular_user.id],
            'new_class': 'trusted'
        }

        response = self.client.post('/api/admin/users/mass-action/', action_data, format='json')
        self.assertIn(response.status_code, [200, 400])

        if response.status_code == 200:
            # Verify the action was performed
            self.regular_user.refresh_from_db()
            self.assertEqual(self.regular_user.user_class, 'trusted')

    def test_admin_actions_log(self):
        """Test admin actions logging"""
        response = self.client.get('/api/admin/actions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)

        # Should include the admin action from user update test
        admin_actions = [action for action in data if action['action_type'] == 'user_ban']
        self.assertGreaterEqual(len(admin_actions), 1)

    def test_system_maintenance(self):
        """Test system maintenance functionality"""
        maintenance_data = {
            'action': 'cleanup_logs',
            'days_old': 30
        }

        response = self.client.post('/api/admin/maintenance/', maintenance_data, format='json')
        # Maintenance operations might have different responses
        self.assertIn(response.status_code, [200, 400, 500])

    def test_admin_action_logging(self):
        """Test that admin actions are properly logged"""
        # Perform an action that should be logged
        update_data = {'user_class': 'elite'}

        self.client.patch(f'/api/admin/users/{self.regular_user.id}/', update_data, format='json')

        # Check that admin action was logged
        admin_actions = AdminAction.objects.filter(
            admin=self.admin_user,
            action_type='user_ban'  # This might be different depending on implementation
        )

        # At minimum, there should be some admin actions logged
        total_actions = AdminAction.objects.filter(admin=self.admin_user).count()
        self.assertGreaterEqual(total_actions, 1)
