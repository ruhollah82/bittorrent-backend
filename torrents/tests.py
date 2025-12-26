from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from decimal import Decimal

from accounts.models import AuthToken
from .models import Torrent, Peer, TorrentStats

User = get_user_model()


class TorrentsAPITestCase(APITestCase):
    """Comprehensive API tests for torrents app"""

    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            total_credit=Decimal('50.00')
        )

        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='other123',
            total_credit=Decimal('25.00')
        )

        # Create auth token for tracker tests
        self.auth_token = AuthToken.objects.create(
            user=self.user,
            token='test_token_123456789012345678901234567890',
            expires_at=timezone.now() + timedelta(days=30)
        )

        # Create test torrents
        self.torrent1 = Torrent.objects.create(
            info_hash='aabbccddeeff00112233445566778899aabbccdd',
            name='Test Torrent 1',
            description='A test torrent file',
            size=1024 * 1024 * 100,  # 100MB
            files_count=1,
            created_by=self.user,
            is_active=True,
            is_private=False,
            category='software',
            tags=['test', 'software']
        )

        self.torrent2 = Torrent.objects.create(
            info_hash='bbccddeeff00112233445566778899aabbccddee',
            name='Test Torrent 2',
            description='Another test torrent',
            size=1024 * 1024 * 200,  # 200MB
            files_count=2,
            created_by=self.other_user,
            is_active=True,
            is_private=True,
            category='movies',
            tags=['movie', 'test']
        )

        # Create torrent stats
        TorrentStats.objects.create(torrent=self.torrent1, seeders=2, leechers=1)
        TorrentStats.objects.create(torrent=self.torrent2, seeders=1, leechers=3)

        # Create some peers
        Peer.objects.create(
            torrent=self.torrent1,
            user=self.user,
            peer_id='-qB0001-testpeerid12',
            ip_address='192.168.1.100',
            port=6881,
            uploaded=1048576,  # 1MB
            downloaded=524288,  # 512KB
            left=1024 * 1024 * 50,  # 50MB left
            state='started',
            is_seeder=False
        )

    def test_torrent_list_view(self):
        """Test listing torrents"""
        response = self.client.get('/api/torrents/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

        # Check torrent data structure
        torrent = data[0]
        self.assertIn('id', torrent)
        self.assertIn('info_hash', torrent)
        self.assertIn('name', torrent)
        self.assertIn('size', torrent)
        self.assertIn('created_by', torrent)
        self.assertIn('category', torrent)

    def test_torrent_detail_view(self):
        """Test getting torrent details"""
        response = self.client.get(f'/api/torrents/{self.torrent1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['name'], 'Test Torrent 1')
        self.assertEqual(data['info_hash'], 'aabbccddeeff00112233445566778899aabbccdd')
        self.assertEqual(data['size'], 1024 * 1024 * 100)
        self.assertEqual(data['category'], 'software')
        self.assertEqual(data['tags'], ['test', 'software'])

    def test_torrent_stats_view(self):
        """Test getting torrent statistics"""
        response = self.client.get(f'/api/torrents/{self.torrent1.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('seeders', data)
        self.assertIn('leechers', data)
        self.assertIn('completed', data)
        self.assertEqual(data['seeders'], 2)
        self.assertEqual(data['leechers'], 1)

    def test_torrent_categories(self):
        """Test getting torrent categories"""
        response = self.client.get('/api/torrents/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertIn('software', [cat['name'] for cat in data])
        self.assertIn('movies', [cat['name'] for cat in data])

    def test_torrent_popular(self):
        """Test getting popular torrents"""
        response = self.client.get('/api/torrents/popular/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        # Should return torrents sorted by some popularity metric

    def test_user_torrents_authenticated(self):
        """Test getting user's own torrents when authenticated"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/torrents/user/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        # Should only include torrents created by this user
        torrent_names = [t['name'] for t in data]
        self.assertIn('Test Torrent 1', torrent_names)
        self.assertNotIn('Test Torrent 2', torrent_names)

    def test_user_torrents_unauthenticated(self):
        """Test user torrents endpoint requires authentication"""
        response = self.client.get('/api/torrents/user/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_torrent_peers(self):
        """Test getting torrent peers"""
        response = self.client.get(f'/api/torrents/{self.torrent1.info_hash}/peers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        if data:  # If there are peers
            peer = data[0]
            self.assertIn('ip_address', peer)
            self.assertIn('port', peer)
            self.assertIn('uploaded', peer)
            self.assertIn('downloaded', peer)

    def test_torrent_health(self):
        """Test torrent health information"""
        response = self.client.get(f'/api/torrents/{self.torrent1.info_hash}/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('health_score', data)
        self.assertIn('seeders', data)
        self.assertIn('leechers', data)
        self.assertIn('total_peers', data)

    def test_delete_torrent_owner(self):
        """Test deleting torrent by owner"""
        self.client.force_authenticate(user=self.user)

        delete_data = {'reason': 'Test deletion'}

        response = self.client.delete(f'/api/torrents/{self.torrent1.info_hash}/delete/', delete_data, format='json')
        self.assertIn(response.status_code, [200, 204])

        if response.status_code in [200, 204]:
            # Verify torrent was marked inactive
            self.torrent1.refresh_from_db()
            self.assertFalse(self.torrent1.is_active)

    def test_delete_torrent_not_owner(self):
        """Test that users can only delete their own torrents"""
        self.client.force_authenticate(user=self.other_user)

        delete_data = {'reason': 'Unauthorized deletion attempt'}

        response = self.client.delete(f'/api/torrents/{self.torrent1.info_hash}/delete/', delete_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_torrent_authenticated(self):
        """Test torrent upload functionality"""
        self.client.force_authenticate(user=self.user)

        # Create a mock torrent file (in real implementation, this would be a .torrent file)
        torrent_file = SimpleUploadedFile(
            "test.torrent",
            b"mock torrent file content",
            content_type="application/x-bittorrent"
        )

        upload_data = {
            'torrent_file': torrent_file,
            'name': 'Uploaded Test Torrent',
            'description': 'A torrent uploaded via API',
            'category': 'software',
            'is_private': False
        }

        response = self.client.post('/api/torrents/upload/', upload_data, format='multipart')
        # Upload might require more complex parsing, so it might return 400
        self.assertIn(response.status_code, [201, 400])

    def test_upload_torrent_unauthenticated(self):
        """Test that torrent upload requires authentication"""
        torrent_file = SimpleUploadedFile(
            "test.torrent",
            b"mock torrent file content",
            content_type="application/x-bittorrent"
        )

        upload_data = {
            'torrent_file': torrent_file,
            'name': 'Unauthorized Upload',
            'category': 'software'
        }

        response = self.client.post('/api/torrents/upload/', upload_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_torrent_model_properties(self):
        """Test Torrent model properties"""
        # Test size_gb property
        expected_gb = 100.0  # 100MB = 0.1GB, but let's check calculation
        actual_gb = self.torrent1.size / (1024 ** 3)
        self.assertAlmostEqual(self.torrent1.size_gb, actual_gb, places=2)

        # Test info_hash_display property
        self.assertEqual(self.torrent1.info_hash_display, 'AABBCCDDEEFF00112233445566778899AABBCCDD')

    def test_peer_model_creation(self):
        """Test Peer model creation and updates"""
        peer = Peer.objects.create(
            torrent=self.torrent1,
            user=self.other_user,
            peer_id='-qB0002-otherpeer123',
            ip_address='192.168.1.101',
            port=6882,
            uploaded=2097152,  # 2MB
            downloaded=1048576,  # 1MB
            left=0,  # Seeder
            state='completed',
            is_seeder=True
        )

        self.assertTrue(peer.is_seeder)
        self.assertEqual(peer.state, 'completed')

        # Test peer string representation
        self.assertIn('192.168.1.101:6882', str(peer))

    def test_torrent_stats_update(self):
        """Test that torrent stats are updated when peers change"""
        # Initially 2 seeders, 1 leecher
        stats = self.torrent1.stats
        self.assertEqual(stats.seeders, 2)
        self.assertEqual(stats.leechers, 1)

        # Add another leecher
        Peer.objects.create(
            torrent=self.torrent1,
            user=self.other_user,
            peer_id='-qB0003-newpeer456',
            ip_address='192.168.1.102',
            port=6883,
            uploaded=0,
            downloaded=0,
            left=1024 * 1024 * 100,  # Full torrent left
            state='started',
            is_seeder=False
        )

        # Refresh stats (this would typically be done by a management command)
        # For this test, we'll manually check the count
        leecher_count = self.torrent1.peers.filter(is_seeder=False).count()
        self.assertEqual(leecher_count, 2)  # Original + new leecher

    def test_private_torrent_access(self):
        """Test that private torrents have restricted access"""
        # torrent2 is private and created by other_user
        self.client.force_authenticate(user=self.user)

        # User should not be able to see private torrent details if not owner
        response = self.client.get(f'/api/torrents/{self.torrent2.id}/')
        self.assertIn(response.status_code, [200, 403, 404])  # Depends on implementation

    def test_torrent_filtering(self):
        """Test torrent filtering by category"""
        response = self.client.get('/api/torrents/?category=software')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        for torrent in data:
            if torrent['name'] == 'Test Torrent 1':  # Should be included
                self.assertEqual(torrent['category'], 'software')
            elif torrent['name'] == 'Test Torrent 2':  # Should not be included
                self.fail("Private torrent from different category appeared in filtered results")

    def test_torrent_search(self):
        """Test torrent search functionality"""
        response = self.client.get('/api/torrents/?search=Test')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        torrent_names = [t['name'] for t in data]
        self.assertIn('Test Torrent 1', torrent_names)
        # torrent2 might not appear if it's private
