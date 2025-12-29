"""
Simple test script for the refactored tracker
"""
import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory

# Add the project root to Python path
sys.path.insert(0, '/home/ruhollah/Projects/bittorrent-backend')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bittorrent_backend.settings')
django.setup()

from tracker.core.server import TrackerServer
from tracker.core.http_parser import parse_http_request
from tracker.core.bencode import encode_response, create_announce_response


def test_basic_tracker():
    """Test basic tracker functionality"""
    print("Testing basic tracker functionality...")

    # Create tracker server
    server = TrackerServer()

    # Test announce parameters
    test_params = {
        'action': 1,  # ANNOUNCE
        'info_hash': 'aaaaaaaaaaaaaaaaaaaa',  # 20 bytes as hex
        'peer_id': 'bbbbbbbbbbbbbbbbbbbb',  # 20 bytes as hex
        'ip': '192.168.1.100',
        'port': 6881,
        'uploaded': 0,
        'downloaded': 0,
        'left': 1000000,
        'event': 'started',
        'type': 'http'
    }

    try:
        # Handle announce
        response = server.handle_announce(test_params)
        print(f"Announce response: {response}")

        # Test scrape
        scrape_params = {
            'action': 2,  # SCRAPE
            'info_hash': ['aaaaaaaaaaaaaaaaaaaa']
        }
        scrape_response = server.handle_scrape(scrape_params)
        print(f"Scrape response: {scrape_response}")

        print("✓ Basic tracker test passed!")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bencode():
    """Test bencode functionality"""
    print("Testing bencode functionality...")

    try:
        # Test announce response
        response = create_announce_response(
            complete=5,
            incomplete=10,
            peers=[
                {'ip': '192.168.1.1', 'port': 6881, 'peer_id': 'peer1'},
                {'ip': '192.168.1.2', 'port': 6882, 'peer_id': 'peer2'}
            ],
            interval=600
        )

        encoded = encode_response(response)
        print(f"Encoded response length: {len(encoded)} bytes")
        print("✓ Bencode test passed!")
        return True

    except Exception as e:
        print(f"✗ Bencode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Running tracker tests...\n")

    success = True
    success &= test_basic_tracker()
    print()
    success &= test_bencode()

    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)
