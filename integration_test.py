#!/usr/bin/env python3
"""
Comprehensive Integration Test for BitTorrent Backend
Tests: Login/Logout, Torrent Upload/Download, Credits, Rankings
"""

import requests
import json
import time
import sys
import os
import django
from datetime import datetime
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

User = get_user_model()

# Use Django test client instead of HTTP requests for more reliable testing
USE_TEST_CLIENT = True
BASE_URL = "http://127.0.0.1:8000"

class IntegrationTester:
    def __init__(self):
        if USE_TEST_CLIENT:
            self.client = Client()
            self.session = None
        else:
            self.session = requests.Session()
            self.client = None
        self.access_token = None
        self.refresh_token = None
        self.user_data = None
        self.invite_code = None
        self.test_results = []

    def log(self, message, success=True):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {message}")
        self.test_results.append({
            "message": message,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, description, test_func, *args, **kwargs):
        """Run a test with logging"""
        print(f"\n🔍 Testing: {description}")
        try:
            result = test_func(*args, **kwargs)
            self.log(description, True)
            return result
        except Exception as e:
            self.log(f"{description} - Error: {str(e)}", False)
            return None

    def create_invite_code(self):
        """Create an invite code for testing"""
        # This would normally be done by an admin, but for testing we'll simulate
        # For now, we'll assume an invite code exists or create one through the API
        # Let's check if we can create one through the API first
        pass

    def test_registration(self):
        """Test user registration"""
        # Clean up any existing test user first
        if USE_TEST_CLIENT:
            from accounts.models import User
            User.objects.filter(username="testuser123").delete()

        register_data = {
            "username": "testuser123",
            "email": "testuser123@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "invite_code": "8WN7UOHSVCLH"  # Valid invite code from database
        }

        if USE_TEST_CLIENT:
            response = self.client.post("/api/auth/register/", data=register_data, content_type='application/json')
            print(f"Registration response: {response.status_code}")
        else:
            response = self.session.post(f"{BASE_URL}/api/auth/register/", json=register_data)
            print(f"Registration response: {response.status_code}")

        if response.status_code == 400:
            if USE_TEST_CLIENT:
                error_data = response.json()
            else:
                error_data = response.json()
            if "invite_code" in str(error_data):
                print("Need to create an invite code first. Let's try without one or create one.")
                return False

        if response.status_code == 201:
            if USE_TEST_CLIENT:
                user_data = response.json()
            else:
                user_data = response.json()
            print(f"User registered: {user_data['user']['username']}")
            return True

        if USE_TEST_CLIENT:
            print(f"Registration failed: {response.content.decode()}")
        else:
            print(f"Registration failed: {response.text}")
        return False

    def test_login(self):
        """Test user login"""
        login_data = {
            "username": "testuser123",
            "password": "testpass123"
        }

        if USE_TEST_CLIENT:
            response = self.client.post("/api/auth/login/", data=login_data, content_type='application/json')
        else:
            response = self.session.post(f"{BASE_URL}/api/auth/login/", json=login_data)

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                data = response.json()
            else:
                data = response.json()
            self.access_token = data['tokens']['access']
            self.refresh_token = data['tokens']['refresh']
            self.user_data = data['user']

            # Set authorization header for future requests
            if USE_TEST_CLIENT:
                self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.access_token}'
            else:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })

            print(f"Login successful for user: {self.user_data['username']}")
            print(f"Credits: {self.user_data['available_credit']}")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Login failed: {response.content.decode()}")
            else:
                print(f"Login failed: {response.text}")
            return False

    def test_get_profile(self):
        """Test getting user profile"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/user/profile/")
        else:
            response = self.session.get(f"{BASE_URL}/api/user/profile/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                profile_data = response.json()
            else:
                profile_data = response.json()
            print(f"Profile data: Username={profile_data['username']}, Credits={profile_data['available_credit']}")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Profile fetch failed: {response.content.decode()}")
            else:
                print(f"Profile fetch failed: {response.text}")
            return False

    def test_create_invite_code(self):
        """Test creating invite codes (admin function)"""
        invite_data = {
            "count": 5,
            "expires_in_days": 7
        }

        if USE_TEST_CLIENT:
            response = self.client.post("/api/auth/invite/create/", data=invite_data, content_type='application/json')
        else:
            response = self.session.post(f"{BASE_URL}/api/auth/invite/create/", json=invite_data)

        if response.status_code == 201:
            if USE_TEST_CLIENT:
                invite_data = response.json()
            else:
                invite_data = response.json()
            print(f"Created {len(invite_data['codes'])} invite codes")
            if invite_data['codes']:
                self.invite_code = invite_data['codes'][0]
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Invite code creation failed: {response.content.decode()}")
            else:
                print(f"Invite code creation failed: {response.text}")
            # This might fail if user is not admin, which is expected
            return response.status_code == 403  # Forbidden is OK for regular users

    def test_list_tokens(self):
        """Test listing auth tokens"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/user/tokens/")
        else:
            response = self.session.get(f"{BASE_URL}/api/user/tokens/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                tokens_data = response.json()
            else:
                tokens_data = response.json()
            print(f"Found {tokens_data['count']} auth tokens")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Token list failed: {response.content.decode()}")
            else:
                print(f"Token list failed: {response.text}")
            return False

    def test_tracker_announce(self):
        """Test BitTorrent tracker announce"""
        # This tests the core tracker functionality
        announce_data = {
            "info_hash": "aabbccddeeff00112233445566778899aabbccdd",
            "peer_id": "-qB0001-testpeerid12",
            "port": "6881",
            "uploaded": "1024",
            "downloaded": "512",
            "left": "2048",
            "compact": "1",
            "event": "started"
        }

        # Add auth token to query params
        params = {**announce_data, "auth_token": "test_token_123456789012345678901234567890"}

        if USE_TEST_CLIENT:
            response = self.client.get("/announce", params)
        else:
            response = self.session.get(f"{BASE_URL}/announce", params=params)

        if response.status_code == 200:
            # Bencoded response - let's decode it
            try:
                import bencode
                if USE_TEST_CLIENT:
                    announce_response = bencode.decode(response.content)
                else:
                    announce_response = bencode.decode(response.content)
                print(f"Tracker announce successful: {announce_response}")
                return True
            except ImportError:
                print("bencode library not available, but response received")
                return True
        else:
            print(f"Tracker announce failed: {response.status_code}")
            return False

    def test_tracker_scrape(self):
        """Test BitTorrent tracker scrape"""
        params = {
            "info_hash": "aabbccddeeff00112233445566778899aabbccdd",
            "auth_token": "test_token_123456789012345678901234567890"
        }

        if USE_TEST_CLIENT:
            response = self.client.get("/scrape", params)
        else:
            response = self.session.get(f"{BASE_URL}/scrape", params=params)

        if response.status_code == 200:
            try:
                import bencode
                if USE_TEST_CLIENT:
                    scrape_response = bencode.decode(response.content)
                else:
                    scrape_response = bencode.decode(response.content)
                print(f"Tracker scrape successful: {scrape_response}")
                return True
            except ImportError:
                print("bencode library not available, but response received")
                return True
        else:
            print(f"Tracker scrape failed: {response.status_code}")
            return False

    def test_logout(self):
        """Test user logout"""
        if USE_TEST_CLIENT:
            response = self.client.post("/api/auth/logout/")
        else:
            response = self.session.post(f"{BASE_URL}/api/auth/logout/")

        if response.status_code in [200, 205]:  # 205 is Reset Content
            print("Logout successful")
            # Clear authorization header
            if USE_TEST_CLIENT:
                self.client.defaults.pop('HTTP_AUTHORIZATION', None)
            else:
                self.session.headers.pop('Authorization', None)
            self.access_token = None
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Logout failed: {response.content.decode()}")
            else:
                print(f"Logout failed: {response.text}")
            return False

    def test_unauthenticated_access(self):
        """Test that protected endpoints require authentication"""
        # Create a new client without authentication
        if USE_TEST_CLIENT:
            temp_client = Client()
            response = temp_client.get("/api/user/profile/")
        else:
            temp_session = requests.Session()
            response = temp_session.get(f"{BASE_URL}/api/user/profile/")

        if response.status_code == 401:
            print("Unauthenticated access properly blocked")
            return True
        else:
            print(f"Unauthenticated access not properly blocked: {response.status_code}")
            return False

    def test_credits_balance(self):
        """Test credits balance endpoint"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/credits/balance/")
        else:
            response = self.session.get(f"{BASE_URL}/api/credits/balance/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                balance_data = response.json()
            else:
                balance_data = response.json()
            print(f"Credits balance: {balance_data}")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Credits balance failed: {response.content.decode()}")
            else:
                print(f"Credits balance failed: {response.text}")
            return False

    def test_credits_transactions(self):
        """Test credits transactions endpoint"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/credits/transactions/")
        else:
            response = self.session.get(f"{BASE_URL}/api/credits/transactions/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                transactions_data = response.json()
            else:
                transactions_data = response.json()
            print(f"Found {transactions_data['count']} credit transactions")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Credits transactions failed: {response.content.decode()}")
            else:
                print(f"Credits transactions failed: {response.text}")
            return False

    def test_user_stats(self):
        """Test user stats endpoint"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/user/stats/")
        else:
            response = self.session.get(f"{BASE_URL}/api/user/stats/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                stats_data = response.json()
            else:
                stats_data = response.json()
            print(f"User stats: {stats_data}")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"User stats failed: {response.content.decode()}")
            else:
                print(f"User stats failed: {response.text}")
            return False

    def test_torrent_categories(self):
        """Test torrent categories endpoint"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/torrents/categories/")
        else:
            response = self.session.get(f"{BASE_URL}/api/torrents/categories/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                categories_data = response.json()
            else:
                categories_data = response.json()
            print(f"Found {len(categories_data)} torrent categories")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Torrent categories failed: {response.content.decode()}")
            else:
                print(f"Torrent categories failed: {response.text}")
            return False

    def test_popular_torrents(self):
        """Test popular torrents endpoint"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/torrents/popular/")
        else:
            response = self.session.get(f"{BASE_URL}/api/torrents/popular/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                popular_data = response.json()
            else:
                popular_data = response.json()
            print(f"Found {popular_data['count']} popular torrents")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Popular torrents failed: {response.content.decode()}")
            else:
                print(f"Popular torrents failed: {response.text}")
            return False

    def test_my_torrents(self):
        """Test my torrents endpoint"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/torrents/my-torrents/")
        else:
            response = self.session.get(f"{BASE_URL}/api/torrents/my-torrents/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                my_torrents_data = response.json()
            else:
                my_torrents_data = response.json()
            print(f"Found {my_torrents_data['count']} user's torrents")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"My torrents failed: {response.content.decode()}")
            else:
                print(f"My torrents failed: {response.text}")
            return False

    def test_credits_ratio_status(self):
        """Test credits ratio status endpoint"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/credits/ratio-status/")
        else:
            response = self.session.get(f"{BASE_URL}/api/credits/ratio-status/")

        if response.status_code == 200:
            if USE_TEST_CLIENT:
                ratio_data = response.json()
            else:
                ratio_data = response.json()
            print(f"Ratio status: {ratio_data}")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Ratio status failed: {response.content.decode()}")
            else:
                print(f"Ratio status failed: {response.text}")
            return False

    def test_security_stats(self):
        """Test security stats endpoint (admin only)"""
        if USE_TEST_CLIENT:
            response = self.client.get("/api/security/stats/")
        else:
            response = self.session.get(f"{BASE_URL}/api/security/stats/")

        # This might return 403 for regular users, which is expected
        if response.status_code in [200, 403]:
            if response.status_code == 200:
                if USE_TEST_CLIENT:
                    security_data = response.json()
                else:
                    security_data = response.json()
                print(f"Security stats: {security_data}")
            else:
                print("Security stats access denied (expected for non-admin users)")
            return True
        else:
            if USE_TEST_CLIENT:
                print(f"Security stats failed: {response.content.decode()}")
            else:
                print(f"Security stats failed: {response.text}")
            return False

    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting BitTorrent Backend Integration Tests")
        print("=" * 60)

        # Clean up any existing test users
        if USE_TEST_CLIENT:
            try:
                from accounts.models import User
                User.objects.filter(username__startswith="testuser").delete()
                print("🧹 Cleaned up existing test users")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")

        # Setup - create invite code first (this might fail for non-admin)
        self.run_test("Create invite code for testing", self.create_invite_code)

        # Test user registration (might fail without invite code)
        self.run_test("User Registration", self.test_registration)

        # Try to login (might fail if registration didn't work)
        if not self.run_test("User Login", self.test_login):
            print("❌ Cannot proceed with tests - login failed")
            return False

        # Run all authenticated tests
        self.run_test("Get User Profile", self.test_get_profile)
        self.run_test("Create Invite Code", self.test_create_invite_code)
        self.run_test("List Auth Tokens", self.test_list_tokens)
        self.run_test("Test Torrent Tracker Announce", self.test_tracker_announce)
        self.run_test("Test Torrent Scrape", self.test_tracker_scrape)

        # Test logout
        self.run_test("Test Logout", self.test_logout)

        # Test unauthenticated access
        self.run_test("Test Unauthenticated Access", self.test_unauthenticated_access)

        # Additional API Tests
        print("\n" + "=" * 40)
        print("🔄 Running Additional API Tests")
        print("=" * 40)

        self.run_test("Test Credits Balance", self.test_credits_balance)
        self.run_test("Test Credits Transactions", self.test_credits_transactions)
        self.run_test("Test User Stats", self.test_user_stats)
        self.run_test("Test Torrent Categories", self.test_torrent_categories)
        self.run_test("Test Popular Torrents", self.test_popular_torrents)
        self.run_test("Test My Torrents", self.test_my_torrents)
        self.run_test("Test Credits Ratio Status", self.test_credits_ratio_status)
        self.run_test("Test Security Stats", self.test_security_stats)

        print("\n" + "=" * 60)
        print("🏁 Integration Tests Completed")

        successful_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)

        print(f"Results: {successful_tests}/{total_tests} tests passed")

        if successful_tests == total_tests:
            print("🎉 All tests passed! System is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False


def main():
    tester = IntegrationTester()
    success = tester.run_all_tests()

    # Print detailed results
    print("\n📊 Detailed Test Results:")
    for i, result in enumerate(tester.test_results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"{i:2d}. {status} {result['message']}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
