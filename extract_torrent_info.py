#!/usr/bin/env python3
"""
Extract info hash and details from a torrent file
"""
import sys
import bencode
import hashlib

if len(sys.argv) < 2:
    print("Usage: python extract_torrent_info.py <torrent_file>")
    sys.exit(1)

torrent_path = sys.argv[1]

try:
    with open(torrent_path, 'rb') as f:
        torrent_data = bencode.decode(f.read())
    
    # Get info hash
    info = torrent_data[b'info']
    info_bencoded = bencode.encode(info)
    info_hash = hashlib.sha1(info_bencoded).hexdigest()
    
    print(f"Info Hash: {info_hash}")
    print(f"Torrent Name: {torrent_data[b'info'][b'name'].decode('utf-8')}")
    
    if b'length' in torrent_data[b'info']:
        size = torrent_data[b'info'][b'length']
        print(f"File Size: {size / (1024**3):.2f} GB ({size:,} bytes)")
    else:
        # Multi-file torrent
        total_size = sum(f[b'length'] for f in torrent_data[b'info'][b'files'])
        print(f"Total Size: {total_size / (1024**3):.2f} GB ({total_size:,} bytes)")
        print(f"Files: {len(torrent_data[b'info'][b'files'])}")
    
    if b'announce' in torrent_data:
        print(f"Tracker: {torrent_data[b'announce'].decode('utf-8')}")
    
    if b'piece length' in torrent_data[b'info']:
        print(f"Piece Size: {torrent_data[b'info'][b'piece length'] / (1024**2):.2f} MB")
    
    print(f"\nUse this info hash for testing:")
    print(f"  python test_tracker_simulator.py {info_hash} <auth_token>")
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

