import bencode
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from unittest.mock import patch
from torrents.models import Torrent, Peer, TorrentStats
from accounts.models import AuthToken
from security.models import IPBlock, SuspiciousActivity, AnnounceLog
from logging_monitoring.models import SystemLog
from credits.models import CreditTransaction
from decimal import Decimal

User = get_user_model()


class TrackerViewsTestCase(TestCase):
    """Comprehensive test cases for tracker views"""

    def setUp(self):
        # Clear cache to avoid rate limiting between tests
        cache.clear()

        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Set credit fields
        self.user.total_credit = Decimal('10.0')
        self.user.save()

        # Create test torrent
        self.torrent = Torrent.objects.create(
            info_hash='aabbccddeeff00112233445566778899aabbccdd',
            name='Test Torrent',
            size=1024 * 1024 * 100,  # 100MB
            created_by=self.user,
            is_active=True
        )

        # Create auth token
        self.auth_token = AuthToken.objects.create(
            user=self.user,
            token='test_token_123456789012345678901234567890',
            expires_at=timezone.now() + timezone.timedelta(days=30)
        )

        # Create torrent stats
        self.torrent_stats = TorrentStats.objects.create(torrent=self.torrent)

    def test_announce_endpoint_basic(self):
        """Test basic announce endpoint functionality"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')

        # Verify successful response
        response_data = bencode.decode(response.content)
        self.assertIn('interval', response_data)
        self.assertIn('peers', response_data)

        # Verify peer was created
        peer = Peer.objects.get(torrent=self.torrent, user=self.user)
        self.assertEqual(peer.peer_id, '-qB0001-testpeerid12')
        self.assertEqual(peer.port, 6881)
        self.assertEqual(peer.uploaded, 1024)

        # Verify announce log was created
        announce_log = AnnounceLog.objects.get(user=self.user, torrent=self.torrent)
        self.assertEqual(announce_log.event, 'started')

    def test_announce_invalid_token(self):
        """Test announce with invalid token"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': 'invalid_token'
        }

        response = self.client.get(announce_url, params)
        self.assertEqual(response.status_code, 200)

        # Decode bencoded response
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'Invalid auth_token')

    def test_announce_missing_auth_token(self):
        """Test announce without auth token"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started'
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'Missing auth_token')

    def test_announce_missing_required_params(self):
        """Test announce with missing required parameters"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'auth_token': self.auth_token.token
            # Missing peer_id, port, uploaded, downloaded, left, compact, event
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertIn('Missing parameter', response_data['failure reason'])

    def test_announce_invalid_info_hash(self):
        """Test announce with invalid info_hash format"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'invalid_hash',  # Not 40 hex characters
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'Invalid info_hash format')

    def test_announce_invalid_peer_id(self):
        """Test announce with invalid peer_id length"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': 'short',  # Too short
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'Invalid peer_id length')

    def test_announce_invalid_port(self):
        """Test announce with invalid port number"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '99999',  # Invalid port
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'Invalid port number')

    def test_announce_torrent_not_found(self):
        """Test announce for non-existent torrent"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'ffffffffffffffffffffffffffffffffffffffff',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'Torrent not found')

    def test_announce_ip_blocked(self):
        """Test announce from blocked IP"""
        # Create IP block
        IPBlock.objects.create(
            ip_address='127.0.0.1',
            reason='Test block',
            is_active=True
        )

        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'IP blocked')

    @override_settings(BITTORRENT_SETTINGS={'MAX_ANNOUNCE_RATE': 0})  # Rate limit to 0
    def test_announce_rate_limit_exceeded(self):
        """Test announce rate limiting"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)
        self.assertEqual(response_data['failure reason'], 'Rate limit exceeded')

    def test_announce_completed_event(self):
        """Test announce with completed event"""
        announce_url = reverse('tracker:announce')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024000',
            'downloaded': '1024000',
            'left': '0',
            'compact': '1',
            'event': 'completed',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params)
        self.assertEqual(response.status_code, 200)

        response_data = bencode.decode(response.content)
        self.assertIn('complete', response_data)

    def test_announce_compact_vs_dictionary(self):
        """Test both compact and dictionary peer list formats"""
        # Create another peer for testing peer lists
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_token = AuthToken.objects.create(
            user=other_user,
            token='other_token_123456789012345678901234567',
            expires_at=timezone.now() + timezone.timedelta(days=30)
        )

        # First peer announces
        Peer.objects.create(
            torrent=self.torrent,
            user=other_user,
            peer_id='-qB0001-otherpeer12',
            ip_address='192.168.1.2',
            port=6882,
            uploaded=2048,
            downloaded=1024,
            left=1024,
            state='started',
            last_announced=timezone.now()
        )

        announce_url = reverse('tracker:announce')

        # Test compact format
        params_compact = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params_compact)
        response_data = bencode.decode(response.content)
        self.assertIn('peers', response_data)
        # Compact format returns bytes
        self.assertIsInstance(response_data['peers'], bytes)

        # Test dictionary format
        params_dict = params_compact.copy()
        params_dict['compact'] = '0'

        response = self.client.get(announce_url, params_dict)
        response_data = bencode.decode(response.content)
        self.assertIn('peers', response_data)
        # Dictionary format returns list
        self.assertIsInstance(response_data['peers'], list)

    def test_scrape_endpoint(self):
        """Test basic scrape endpoint"""
        scrape_url = reverse('tracker:scrape')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(scrape_url, params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')

        response_data = bencode.decode(response.content)
        self.assertIn('files', response_data)

    def test_scrape_multiple_info_hashes(self):
        """Test scrape with multiple info hashes"""
        # Create another torrent
        torrent2 = Torrent.objects.create(
            info_hash='bbccddeeff00112233445566778899aabbccddee',
            name='Test Torrent 2',
            size=1024 * 1024 * 200,  # 200MB
            created_by=self.user,
            is_active=True
        )
        TorrentStats.objects.create(torrent=torrent2)

        scrape_url = reverse('tracker:scrape')
        params = {
            'info_hash': ['aabbccddeeff00112233445566778899aabbccdd', 'bbccddeeff00112233445566778899aabbccddee'],
            'auth_token': self.auth_token.token
        }

        response = self.client.get(scrape_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('files', response_data)
        self.assertEqual(len(response_data['files']), 2)

    def test_scrape_all_torrents(self):
        """Test scrape without specific info hashes"""
        scrape_url = reverse('tracker:scrape')
        params = {
            'auth_token': self.auth_token.token
        }

        response = self.client.get(scrape_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('files', response_data)

    def test_scrape_invalid_token(self):
        """Test scrape with invalid token"""
        scrape_url = reverse('tracker:scrape')
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'auth_token': 'invalid_token'
        }

        response = self.client.get(scrape_url, params)
        response_data = bencode.decode(response.content)
        self.assertIn('failure reason', response_data)

    def test_announce_credit_transaction(self):
        """Test credit transaction creation on upload"""
        # Set initial credit
        self.user.total_credit = Decimal('5.0')
        self.user.save()

        announce_url = reverse('tracker:announce')

        # First announce with small upload
        params1 = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',  # 1KB
            'downloaded': '0',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params1)
        self.assertEqual(response.status_code, 200)

        # Second announce with larger upload to trigger credit transaction
        params2 = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '104857600',  # 100MB
            'downloaded': '0',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }

        response = self.client.get(announce_url, params2)
        self.assertEqual(response.status_code, 200)

        # Check if credit transaction was created
        credit_tx = CreditTransaction.objects.filter(
            user=self.user,
            torrent=self.torrent,
            transaction_type='upload'
        ).first()
        self.assertIsNotNone(credit_tx)
        self.assertGreater(credit_tx.amount, 0)

    def test_announce_suspicious_activity_detection(self):
        """Test suspicious activity detection"""
        announce_url = reverse('tracker:announce')

        # First announce to establish baseline
        params = {
            'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
            'peer_id': '-qB0001-testpeerid12',
            'port': '6881',
            'uploaded': '1024',
            'downloaded': '512',
            'left': '2048',
            'compact': '1',
            'event': 'started',
            'auth_token': self.auth_token.token
        }
        self.client.get(announce_url, params)

        # Second announce with suspicious upload amount
        params['uploaded'] = '1048576000'  # 1GB upload in one announce (suspicious)
        self.client.get(announce_url, params)

        # Check if suspicious activity was logged
        suspicious = SuspiciousActivity.objects.filter(
            user=self.user,
            activity_type='announce_anomaly'
        ).first()
        self.assertIsNotNone(suspicious)
        self.assertIn('excessive_upload', suspicious.description)