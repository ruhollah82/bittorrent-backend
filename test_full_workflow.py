#!/usr/bin/env python
"""
Complete BitTorrent workflow test
Tests torrent creation, seeding, and leeching with the new tracker
"""
import os
import sys
import time
import hashlib
import bencode
import requests
from urllib.parse import quote

# Add project to path
sys.path.insert(0, '/home/ruhollah/Projects/bittorrent-backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from tracker.core.server import TrackerServer
from tracker.core.bencode import encode_response, create_announce_response

def create_test_torrent():
    """Create a simple test torrent file"""
    # Create a small test file
    test_file = '/tmp/test_file.txt'
    with open(test_file, 'w') as f:
        f.write('This is a test file for BitTorrent tracker testing.\n' * 100)

    # Calculate piece hashes
    piece_length = 32768  # 32KB pieces
    pieces = b''

    with open(test_file, 'rb') as f:
        while True:
            piece = f.read(piece_length)
            if not piece:
                break
            pieces += hashlib.sha1(piece).digest()

    # Create torrent structure
    torrent = {
        'announce': 'http://127.0.0.1:8000/announce',
        'info': {
            'name': 'test_file.txt',
            'length': os.path.getsize(test_file),
            'piece length': piece_length,
            'pieces': pieces
        }
    }

    # Write torrent file
    torrent_file = '/tmp/test.torrent'
    with open(torrent_file, 'wb') as f:
        f.write(bencode.encode(torrent))

    # Calculate info_hash
    info_hash = hashlib.sha1(bencode.encode(torrent['info'])).hexdigest()

    print(f"Created test torrent:")
    print(f"  File: {test_file}")
    print(f"  Torrent: {torrent_file}")
    print(f"  Info hash: {info_hash}")
    print(f"  Size: {torrent['info']['length']} bytes")

    return torrent_file, test_file, info_hash

def test_tracker_workflow():
    """Test the complete tracker workflow"""
    print("=== Testing Complete BitTorrent Tracker Workflow ===\n")

    # Create test torrent
    torrent_file, content_file, info_hash = create_test_torrent()
    print()

    # Initialize tracker
    tracker = TrackerServer(http=True, udp=True, ws=True)
    print("✓ Tracker initialized\n")

    # Simulate torrent registration (in real app, this would be in Django DB)
    # For testing, we'll manually add it to the tracker
    swarm = tracker.create_swarm(info_hash)
    print("✓ Torrent registered with tracker\n")

    # Simulate seeder announcing
    print("=== Simulating Seeder ===")
    seeder_params = {
        'info_hash': info_hash,
        'peer_id': '-TR4000-seeder123456',
        'ip': '192.168.1.100',
        'port': 51413,
        'uploaded': 0,
        'downloaded': 0,
        'left': 0,  # Seeder has complete file
        'event': 'started',
        'type': 'http',
        'numwant': 50
    }

    seeder_response = tracker.handle_announce(seeder_params)
    print(f"Seeder announce response: {seeder_response}")
    assert seeder_response['complete'] == 1  # 1 seeder
    assert seeder_response['incomplete'] == 0  # 0 leechers
    print("✓ Seeder successfully announced\n")

    # Simulate leecher announcing
    print("=== Simulating Leecher ===")
    leecher_params = {
        'info_hash': info_hash,
        'peer_id': '-TR4000-leecher12345',
        'ip': '192.168.1.101',
        'port': 51414,
        'uploaded': 0,
        'downloaded': 0,
        'left': 2500,  # Leecher has some left to download
        'event': 'started',
        'type': 'http',
        'numwant': 50
    }

    leecher_response = tracker.handle_announce(leecher_params)
    print(f"Leecher announce response: {leecher_response}")
    assert leecher_response['complete'] == 1  # 1 seeder
    assert leecher_response['incomplete'] == 1  # 1 leecher
    assert len(leecher_response['peers']) == 1  # Should get seeder in peer list
    print("✓ Leecher successfully announced and got peers\n")

    # Test peer list
    peers = leecher_response['peers']
    print(f"Leecher received {len(peers)} peers:")
    for peer in peers:
        print(f"  - {peer['ip']}:{peer['port']} (peer_id: {peer['peer_id'][:8]}...)")
    print()

    # Simulate leecher completing download
    print("=== Simulating Download Completion ===")
    leecher_params['event'] = 'completed'
    leecher_params['left'] = 0
    leecher_params['downloaded'] = 2500

    completion_response = tracker.handle_announce(leecher_params)
    print(f"Completion announce response: {completion_response}")
    assert completion_response['complete'] == 2  # 2 seeders now
    assert completion_response['incomplete'] == 0  # 0 leechers
    print("✓ Leecher completed download and became seeder\n")

    # Test scrape
    print("=== Testing Scrape ===")
    scrape_params = {
        'info_hash': [info_hash]
    }

    scrape_response = tracker.handle_scrape(scrape_params)
    print(f"Scrape response: {scrape_response}")
    assert info_hash.upper() in scrape_response['files']
    stats = scrape_response['files'][info_hash.upper()]
    assert stats['complete'] == 2
    assert stats['incomplete'] == 0
    print("✓ Scrape returned correct statistics\n")

    # Test statistics
    print("=== Testing Statistics ===")
    stats = tracker.get_stats()
    print(f"Tracker stats: {stats}")
    assert stats['torrents'] == 1
    assert stats['active_torrents'] == 1
    assert stats['peers'] == 2
    assert stats['seeders'] == 2
    assert stats['leechers'] == 0
    print("✓ Tracker statistics are correct\n")

    # Clean up
    os.remove(torrent_file)
    os.remove(content_file)

    print("🎉 All tests passed! BitTorrent tracker is working correctly.")
    print("\nThe tracker successfully:")
    print("- Registered torrents")
    print("- Handled peer announcements")
    print("- Provided peer lists")
    print("- Tracked download completion")
    print("- Generated scrape statistics")
    print("- Maintained accurate statistics")

if __name__ == '__main__':
    test_tracker_workflow()
