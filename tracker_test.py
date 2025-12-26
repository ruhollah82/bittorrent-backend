#!/usr/bin/env python3
"""
Test BitTorrent Tracker Functionality
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_tracker_functionality():
    """Test tracker announce and scrape with valid auth token"""
    print("🔍 Testing BitTorrent Tracker Functionality")
    print("=" * 50)

    # Test Announce
    print("\n📡 Testing Tracker Announce...")
    announce_params = {
        "info_hash": "aabbccddeeff00112233445566778899aabbccdd",
        "peer_id": "-qB0001-testpeerid12",
        "port": "6881",
        "uploaded": "1024",
        "downloaded": "512",
        "left": "2048",
        "compact": "1",
        "event": "started",
        "auth_token": "test_token_123456789012345678901234567890"
    }

    response = requests.get(f"{BASE_URL}/announce", params=announce_params)
    print(f"Announce Status: {response.status_code}")

    if response.status_code == 200:
        try:
            import bencode
            data = bencode.decode(response.content)
            print(f"Announce Response: {data}")
            if 'failure reason' in data:
                print(f"❌ Announce failed: {data['failure reason']}")
            else:
                print("✅ Announce successful!")
        except ImportError:
            print("✅ Announce response received (bencode not available)")
    else:
        print(f"❌ Announce failed with status {response.status_code}")

    # Test Scrape
    print("\n🔍 Testing Tracker Scrape...")
    scrape_params = {
        "info_hash": "aabbccddeeff00112233445566778899aabbccdd",
        "auth_token": "test_token_123456789012345678901234567890"
    }

    response = requests.get(f"{BASE_URL}/scrape", params=scrape_params)
    print(f"Scrape Status: {response.status_code}")

    if response.status_code == 200:
        try:
            import bencode
            data = bencode.decode(response.content)
            print(f"Scrape Response: {data}")
            if 'failure reason' in data:
                print(f"❌ Scrape failed: {data['failure reason']}")
            else:
                print("✅ Scrape successful!")
        except ImportError:
            print("✅ Scrape response received (bencode not available)")
    else:
        print(f"❌ Scrape failed with status {response.status_code}")

def test_unauthenticated_access():
    """Test that unauthenticated access is properly blocked"""
    print("\n🔒 Testing Unauthenticated Access Control...")

    # Test profile endpoint without auth
    response = requests.get(f"{BASE_URL}/api/user/profile/")
    print(f"Profile without auth: {response.status_code}")

    if response.status_code == 401:
        print("✅ Profile properly protected")
    else:
        print(f"❌ Profile not properly protected: {response.status_code}")
        print(f"Response: {response.text[:200]}...")

    # Test tokens endpoint without auth
    response = requests.get(f"{BASE_URL}/api/user/tokens/")
    print(f"Tokens without auth: {response.status_code}")

    if response.status_code == 401:
        print("✅ Tokens properly protected")
    else:
        print(f"❌ Tokens not properly protected: {response.status_code}")

if __name__ == "__main__":
    test_tracker_functionality()
    test_unauthenticated_access()
    print("\n🏁 Tracker Tests Complete!")
