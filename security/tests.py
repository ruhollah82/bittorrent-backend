from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import SuspiciousActivity, IPBlock, AnnounceLog, RateLimit
from accounts.models import User

User = get_user_model()


class SecurityModelsTestCase(TestCase):
    """Test cases for security models"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_suspicious_activity_creation(self):
        """Test creating suspicious activity"""
        activity = SuspiciousActivity.objects.create(
            user=self.user,
            activity_type='fake_upload',
            severity='high',
            description='Test suspicious activity',
            ip_address='192.168.1.1'
        )

        self.assertEqual(activity.activity_type, 'fake_upload')
        self.assertEqual(activity.severity, 'high')
        self.assertFalse(activity.is_resolved)

    def test_ip_block_creation(self):
        """Test creating IP block"""
        block = IPBlock.objects.create(
            ip_address='192.168.1.100',
            reason='Test block',
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )

        self.assertEqual(block.ip_address, '192.168.1.100')
        self.assertTrue(block.is_active)
        self.assertFalse(block.is_expired())

    def test_announce_log_creation(self):
        """Test creating announce log"""
        log = AnnounceLog.objects.create(
            user=self.user,
            torrent_id='aabbccddeeff00112233445566778899aabbccdd',
            event='started',
            uploaded=1024,
            downloaded=512,
            left=2048,
            ip_address='192.168.1.1',
            port=6881,
            peer_id='-qB0001-testpeerid12',
            is_suspicious=False
        )

        self.assertEqual(log.event, 'started')
        self.assertEqual(log.uploaded, 1024)
        self.assertFalse(log.is_suspicious)


class SecurityViewsTestCase(TestCase):
    """Test cases for security views"""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')

    def test_security_stats_view(self):
        """Test security stats endpoint"""
        response = self.client.get('/api/security/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_suspicious_activities', response.data)

    def test_suspicious_activities_list(self):
        """Test suspicious activities list endpoint"""
        response = self.client.get('/api/security/suspicious-activities/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)