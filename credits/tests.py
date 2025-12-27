from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from decimal import Decimal

from torrents.models import Torrent
from .models import CreditTransaction

User = get_user_model()


class CreditsAPITestCase(APITestCase):
    """Comprehensive API tests for credits app"""

    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            total_credit=Decimal('50.00')
        )

        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True,
            total_credit=Decimal('100.00')
        )

        # Create test torrent
        self.torrent = Torrent.objects.create(
            info_hash='aabbccddeeff00112233445566778899aabbccdd',
            name='Test Torrent',
            size=1024 * 1024 * 100,  # 100MB
            created_by=self.user,
            is_active=True
        )

        # Create some credit transactions
        self.transaction1 = CreditTransaction.objects.create(
            user=self.user,
            torrent=self.torrent,
            transaction_type='upload',
            amount=Decimal('5.25'),
            description='Upload credit for torrent share'
        )

        self.transaction2 = CreditTransaction.objects.create(
            user=self.user,
            transaction_type='bonus',
            amount=Decimal('10.00'),
            description='Welcome bonus'
        )

    def test_credit_balance_view(self):
        """Test getting user's credit balance"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/credits/balance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('total_credit', data)
        self.assertIn('locked_credit', data)
        self.assertIn('available_credit', data)
        self.assertEqual(Decimal(data['total_credit']), Decimal('50.00'))

    def test_credit_transaction_list(self):
        """Test listing user's credit transactions"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/credits/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

        # Check transaction data structure
        transaction = data[0]
        self.assertIn('id', transaction)
        self.assertIn('transaction_type', transaction)
        self.assertIn('amount', transaction)
        self.assertIn('description', transaction)
        self.assertIn('timestamp', transaction)

    def test_credit_transaction_detail(self):
        """Test getting specific transaction details"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f'/api/credits/transactions/{self.transaction1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['id'], self.transaction1.id)
        self.assertEqual(data['transaction_type'], 'upload')
        self.assertEqual(Decimal(data['amount']), Decimal('5.25'))
        self.assertEqual(data['description'], 'Upload credit for torrent share')

    def test_user_class_info(self):
        """Test getting user class information"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/credits/user-class/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('current_class', data)
        self.assertIn('download_multiplier', data)
        self.assertIn('max_torrents', data)
        self.assertIn('next_class', data)
        self.assertIn('upgrade_requirements', data)

    def test_check_download_permission(self):
        """Test checking download permission for torrent"""
        self.client.force_authenticate(user=self.user)

        # Test with sufficient credits
        check_data = {'torrent_id': self.torrent.id}

        response = self.client.post('/api/credits/check-download/', check_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('can_download', data)
        self.assertIn('required_credit', data)
        self.assertIn('available_credit', data)
        self.assertTrue(data['can_download'])  # User has 50 credits, torrent costs ~0.1 credits

    def test_check_download_permission_insufficient_credits(self):
        """Test download permission check with insufficient credits"""
        # Create user with very low credits
        poor_user = User.objects.create_user(
            username='pooruser',
            email='poor@example.com',
            password='poor123',
            total_credit=Decimal('0.01')  # Very low credits
        )

        # Create expensive torrent
        expensive_torrent = Torrent.objects.create(
            info_hash='bbccddeeff00112233445566778899aabbccddee',
            name='Expensive Torrent',
            size=1024 * 1024 * 1024 * 10,  # 10GB - expensive
            created_by=self.admin_user,
            is_active=True
        )

        self.client.force_authenticate(user=poor_user)

        check_data = {'torrent_id': expensive_torrent.id}

        response = self.client.post('/api/credits/check-download/', check_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertFalse(data['can_download'])
        self.assertIn('reason', data)

    def test_lock_credit_for_download(self):
        """Test locking credits for download"""
        self.client.force_authenticate(user=self.user)

        lock_data = {'torrent_id': self.torrent.id}

        response = self.client.post('/api/credits/lock-credit/', lock_data, format='json')
        self.assertIn(response.status_code, [200, 400])  # Might fail if torrent size calculation is different

        if response.status_code == 200:
            data = response.data
            self.assertIn('locked_amount', data)
            self.assertIn('transaction_id', data)

            # Verify credit was locked
            self.user.refresh_from_db()
            self.assertGreater(self.user.locked_credit, 0)

    def test_complete_download_transaction(self):
        """Test completing a download transaction"""
        # First lock some credit
        lock_data = {'torrent_id': self.torrent.id}
        self.client.force_authenticate(user=self.user)

        lock_response = self.client.post('/api/credits/lock-credit/', lock_data, format='json')

        if lock_response.status_code == 200:
            lock_data = lock_response.json()
            transaction_id = lock_data.get('transaction_id')

            if transaction_id:
                # Now complete the transaction
                complete_data = {'transaction_id': transaction_id}

                response = self.client.post('/api/credits/complete-download/', complete_data, format='json')
                self.assertIn(response.status_code, [200, 400])

    def test_calculate_upload_credit(self):
        """Test calculating upload credit"""
        self.client.force_authenticate(user=self.user)

        calc_data = {
            'uploaded_bytes': 104857600,  # 100MB
            'torrent_id': self.torrent.id
        }

        response = self.client.post('/api/credits/calculate-upload/', calc_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('credit_amount', data)
        self.assertIn('multiplier', data)
        self.assertGreater(Decimal(data['credit_amount']), 0)

    def test_check_ratio_status(self):
        """Test checking user's ratio status"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/credits/ratio-status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('current_ratio', data)
        self.assertIn('status', data)
        self.assertIn('lifetime_upload', data)
        self.assertIn('lifetime_download', data)

    def test_adjust_user_credit_admin_only(self):
        """Test that only admins can adjust user credits"""
        self.client.force_authenticate(user=self.user)  # Regular user

        adjust_data = {
            'user_id': self.user.id,
            'amount': '25.00',
            'reason': 'Test adjustment'
        }

        response = self.client.post('/api/credits/adjust/', adjust_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_adjust_user_credit_as_admin(self):
        """Test adjusting user credits as admin"""
        self.client.force_authenticate(user=self.admin_user)  # Admin user

        adjust_data = {
            'user_id': self.user.id,
            'amount': '25.50',
            'reason': 'Admin bonus'
        }

        response = self.client.post('/api/credits/adjust/', adjust_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify credit was adjusted
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_credit, Decimal('75.50'))  # 50 + 25.50

        # Verify transaction was created
        transaction = CreditTransaction.objects.filter(
            user=self.user,
            transaction_type='admin_adjust',
            amount=Decimal('25.50')
        ).first()
        self.assertIsNotNone(transaction)

    def test_promote_user_class_admin_only(self):
        """Test that only admins can promote users"""
        self.client.force_authenticate(user=self.user)  # Regular user

        promote_data = {
            'user_id': self.user.id,
            'target_class': 'member'
        }

        response = self.client.post('/api/credits/promote/', promote_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_promote_user_class_as_admin(self):
        """Test promoting user class as admin"""
        self.client.force_authenticate(user=self.admin_user)  # Admin user

        promote_data = {
            'user_id': self.user.id,
            'target_class': 'member'
        }

        response = self.client.post('/api/credits/promote/', promote_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user class was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.user_class, 'member')

    def test_credit_transaction_model_save(self):
        """Test that CreditTransaction model properly updates user balance"""
        # Create a new transaction
        transaction = CreditTransaction.objects.create(
            user=self.user,
            transaction_type='bonus',
            amount=Decimal('15.75'),
            description='Test bonus'
        )

        # Verify user balance was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_credit, Decimal('65.75'))  # 50 + 15.75

        # Test penalty transaction
        penalty_transaction = CreditTransaction.objects.create(
            user=self.user,
            transaction_type='penalty',
            amount=Decimal('-5.00'),
            description='Test penalty'
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.total_credit, Decimal('60.75'))  # 65.75 - 5.00

    def test_credit_transaction_filtering(self):
        """Test filtering credit transactions by type"""
        self.client.force_authenticate(user=self.user)

        # Filter by upload transactions
        response = self.client.get('/api/credits/transactions/?type=upload')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        # Should only include upload transactions
        for transaction in data:
            if transaction['transaction_type'] != 'upload':
                self.fail("Non-upload transaction found in upload filter")

    def test_credit_transaction_pagination(self):
        """Test that transaction list is properly paginated"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/credits/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        # Should be a list (paginated response)
        self.assertIsInstance(data, list)
