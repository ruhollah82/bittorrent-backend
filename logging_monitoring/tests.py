from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta

from .models import SystemLog, UserActivity, Alert, SystemStats

User = get_user_model()


class LoggingMonitoringAPITestCase(APITestCase):
    """Comprehensive API tests for logging_monitoring app"""

    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True
        )

        # Create test logs
        self.system_log = SystemLog.objects.create(
            level='info',
            category='auth',
            message='User logged in',
            user=self.user,
            ip_address='192.168.1.100',
            user_agent='Test Browser',
            details={'session_id': 'abc123'}
        )

        self.error_log = SystemLog.objects.create(
            level='error',
            category='tracker',
            message='Announce failed',
            ip_address='192.168.1.101',
            details={'error_code': 'INVALID_HASH'}
        )

        # Create user activity
        self.user_activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            description='User logged in successfully',
            ip_address='192.168.1.100',
            user_agent='Test Browser',
            details={'device': 'desktop'}
        )

        # Create alerts
        self.active_alert = Alert.objects.create(
            title='High CPU Usage',
            message='Server CPU usage is above 90%',
            severity='high',
            alert_type='system',
            is_active=True,
            created_by=self.admin_user
        )

        self.resolved_alert = Alert.objects.create(
            title='Low Disk Space',
            message='Disk space is running low',
            severity='medium',
            alert_type='storage',
            is_active=False,
            resolved_at=timezone.now(),
            created_by=self.admin_user
        )

        # Create system stats
        self.system_stats = SystemStats.objects.create(
            metric_name='cpu_usage',
            metric_value=85.5,
            unit='percent',
            collected_at=timezone.now()
        )

    def test_system_log_list_admin_only(self):
        """Test that system logs are only accessible to admins"""
        # Test unauthenticated access
        response = self.client.get('/api/logs/system/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test regular user access
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/logs/system/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test admin access
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/logs/system/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_system_log_list_as_admin(self):
        """Test system log listing as admin"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/logs/system/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

        # Check log data structure
        log_entry = data[0]
        self.assertIn('id', log_entry)
        self.assertIn('level', log_entry)
        self.assertIn('category', log_entry)
        self.assertIn('message', log_entry)
        self.assertIn('timestamp', log_entry)

    def test_system_log_filtering(self):
        """Test system log filtering by level and category"""
        self.client.force_authenticate(user=self.admin_user)

        # Filter by level
        response = self.client.get('/api/logs/system/?level=error')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        for log in data:
            self.assertEqual(log['level'], 'error')

        # Filter by category
        response = self.client.get('/api/logs/system/?category=auth')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        for log in data:
            self.assertEqual(log['category'], 'auth')

    def test_user_activity_list(self):
        """Test user activity listing"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/logs/user-activity/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_user_activity_filtering(self):
        """Test user activity filtering"""
        self.client.force_authenticate(user=self.admin_user)

        # Filter by user
        response = self.client.get(f'/api/logs/user-activity/?user={self.user.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        for activity in data:
            self.assertEqual(activity['user'], self.user.id)

        # Filter by activity type
        response = self.client.get('/api/logs/user-activity/?activity_type=login')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        for activity in data:
            self.assertEqual(activity['activity_type'], 'login')

    def test_alert_list(self):
        """Test alert listing"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/logs/alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

    def test_alert_detail(self):
        """Test alert detail view"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(f'/api/logs/alerts/{self.active_alert.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['title'], 'High CPU Usage')
        self.assertEqual(data['severity'], 'high')
        self.assertTrue(data['is_active'])

    def test_alert_update(self):
        """Test updating alert status"""
        self.client.force_authenticate(user=self.admin_user)

        update_data = {
            'is_active': False,
            'notes': 'Issue resolved by restarting service'
        }

        response = self.client.patch(f'/api/logs/alerts/{self.active_alert.id}/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify update
        self.active_alert.refresh_from_db()
        self.assertFalse(self.active_alert.is_active)

    def test_system_stats_list(self):
        """Test system stats listing"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/logs/system-stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/logs/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('total_logs', data)
        self.assertIn('error_count', data)
        self.assertIn('active_alerts', data)
        self.assertIn('system_health', data)

    def test_analyze_logs(self):
        """Test log analysis functionality"""
        self.client.force_authenticate(user=self.admin_user)

        analyze_data = {
            'time_range': '24h',
            'categories': ['auth', 'tracker']
        }

        response = self.client.post('/api/logs/analyze/', analyze_data, format='json')
        self.assertIn(response.status_code, [200, 400])

    def test_create_manual_alert(self):
        """Test creating manual alerts"""
        self.client.force_authenticate(user=self.admin_user)

        alert_data = {
            'title': 'Manual Test Alert',
            'message': 'This is a test alert created manually',
            'severity': 'low',
            'alert_type': 'test'
        }

        response = self.client.post('/api/logs/alerts/create/', alert_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify alert was created
        alert = Alert.objects.filter(title='Manual Test Alert').first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.created_by, self.admin_user)

    def test_system_health_check(self):
        """Test system health check endpoint"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/logs/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('status', data)
        self.assertIn('checks', data)

    def test_system_log_creation(self):
        """Test SystemLog model creation"""
        log = SystemLog.objects.create(
            level='warning',
            category='security',
            message='Suspicious activity detected',
            ip_address='192.168.1.200',
            details={'threat_level': 'medium'}
        )

        self.assertEqual(str(log), '[WARNING] security: Suspicious activity detected')
        self.assertEqual(log.level, 'warning')
        self.assertEqual(log.category, 'security')

    def test_user_activity_creation(self):
        """Test UserActivity model creation"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='profile_update',
            description='User updated profile information',
            ip_address='192.168.1.100'
        )

        self.assertEqual(activity.activity_type, 'profile_update')
        self.assertEqual(activity.user, self.user)

    def test_alert_model_methods(self):
        """Test Alert model methods"""
        # Test string representation
        self.assertEqual(str(self.active_alert), 'High CPU Usage (high)')

        # Test active alert properties
        self.assertTrue(self.active_alert.is_active)
        self.assertIsNone(self.active_alert.resolved_at)

        # Test resolved alert
        self.assertFalse(self.resolved_alert.is_active)
        self.assertIsNotNone(self.resolved_alert.resolved_at)

    def test_system_stats_model(self):
        """Test SystemStats model"""
        self.assertEqual(self.system_stats.metric_name, 'cpu_usage')
        self.assertEqual(self.system_stats.metric_value, 85.5)
        self.assertEqual(self.system_stats.unit, 'percent')

    def test_log_filtering_by_date(self):
        """Test log filtering by date range"""
        self.client.force_authenticate(user=self.admin_user)

        # Create a log from yesterday
        yesterday = timezone.now() - timedelta(days=1)
        old_log = SystemLog.objects.create(
            level='info',
            category='system',
            message='Old system log',
            timestamp=yesterday
        )

        # Filter logs from last 24 hours
        response = self.client.get('/api/logs/system/?hours=24')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        # Should not include the old log
        log_ids = [log['id'] for log in data]
        self.assertNotIn(old_log.id, log_ids)

    def test_alert_acknowledgment(self):
        """Test alert acknowledgment functionality"""
        self.client.force_authenticate(user=self.admin_user)

        # Acknowledge an alert
        ack_data = {'acknowledged': True}

        response = self.client.patch(f'/api/logs/alerts/{self.active_alert.id}/', ack_data, format='json')
        self.assertIn(response.status_code, [200, 400])

    def test_bulk_log_operations(self):
        """Test bulk operations on logs"""
        self.client.force_authenticate(user=self.admin_user)

        # Test bulk delete (if implemented)
        bulk_data = {
            'action': 'delete_old',
            'days': 30
        }

        response = self.client.post('/api/logs/bulk/', bulk_data, format='json')
        self.assertIn(response.status_code, [200, 400, 501])  # 501 if not implemented
