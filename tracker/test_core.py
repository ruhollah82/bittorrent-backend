"""
Test the core tracker functionality without Django
"""
import sys
import os
sys.path.insert(0, '/home/ruhollah/Projects/bittorrent-backend')

from tracker.core.server import TrackerServer
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
        'type': 'http',
        'numwant': 50
    }

    try:
        # Handle announce
        response = server.handle_announce(test_params)
        print(f"Announce response: {response}")
        assert 'complete' in response
        assert 'incomplete' in response
        assert 'peers' in response
        assert 'interval' in response

        # Test another peer joining
        test_params2 = test_params.copy()
        test_params2['peer_id'] = 'cccccccccccccccccccc'
        test_params2['ip'] = '192.168.1.101'
        test_params2['port'] = 6882

        response2 = server.handle_announce(test_params2)
        print(f"Second announce response: {response2}")
        assert response2['incomplete'] == 2  # Should have 2 leechers now

        # Test scrape
        scrape_params = {
            'action': 2,  # SCRAPE
            'info_hash': ['aaaaaaaaaaaaaaaaaaaa']
        }
        scrape_response = server.handle_scrape(scrape_params)
        print(f"Scrape response: {scrape_response}")
        assert 'files' in scrape_response
        assert 'aaaaaaaaaaaaaaaaaaaa'.upper() in scrape_response['files']

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
        print(f"Response keys: {list(response.keys())}")

        # Test compact encoding
        response_compact = create_announce_response(
            complete=5,
            incomplete=10,
            peers=[
                {'ip': '192.168.1.1', 'port': 6881, 'peer_id': 'peer1'},
                {'ip': '192.168.1.2', 'port': 6882, 'peer_id': 'peer2'}
            ],
            interval=600,
            compact=True
        )
        encoded_compact = encode_response(response_compact)
        print(f"Compact encoded response length: {len(encoded_compact)} bytes")

        print("✓ Bencode test passed!")
        return True

    except Exception as e:
        print(f"✗ Bencode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_swarm_events():
    """Test swarm event handling"""
    print("Testing swarm event handling...")

    try:
        server = TrackerServer()
        info_hash = 'aaaaaaaaaaaaaaaaaaaa'

        # Test started event
        params_started = {
            'info_hash': info_hash,
            'peer_id': 'peer1peer1peer1peer1p',
            'ip': '192.168.1.100',
            'port': 6881,
            'uploaded': 0,
            'downloaded': 0,
            'left': 1000000,
            'event': 'started',
            'type': 'http',
            'numwant': 50
        }

        response = server.handle_announce(params_started)
        assert response['incomplete'] == 1
        assert response['complete'] == 0

        # Test completed event
        params_completed = params_started.copy()
        params_completed['event'] = 'completed'
        params_completed['left'] = 0
        params_completed['downloaded'] = 1000000

        response = server.handle_announce(params_completed)
        assert response['incomplete'] == 0
        assert response['complete'] == 1

        # Test stopped event
        params_stopped = params_completed.copy()
        params_stopped['event'] = 'stopped'

        response = server.handle_announce(params_stopped)
        assert response['incomplete'] == 0
        assert response['complete'] == 0  # Peer should be removed

        print("✓ Swarm events test passed!")
        return True

    except Exception as e:
        print(f"✗ Swarm events test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Running core tracker tests...\n")

    success = True
    success &= test_basic_tracker()
    print()
    success &= test_bencode()
    print()
    success &= test_swarm_events()

    # Test server stats
    stats = server.get_stats()
    print(f"\nTracker stats: {stats}")

    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)
