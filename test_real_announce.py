#!/usr/bin/env python
"""
Test real HTTP announce requests to debug the torrent not found issue
"""
import requests
import hashlib
import bencode
from urllib.parse import quote

# Load the torrent file
torrent_path = '/home/ruhollah/Music/Indila - Feuille d\'automne.torrent'
with open(torrent_path, 'rb') as f:
    torrent_data = bencode.bdecode(f.read())

# Calculate info_hash
info_hash = hashlib.sha1(bencode.encode(torrent_data['info'])).hexdigest()
print(f"Info hash: {info_hash}")

# URL encode the binary info_hash as transmission-cli would send it
binary_info_hash = bencode.encode(torrent_data['info']['name'].encode('utf-8')[:20])  # This is wrong, let me fix it
# Actually, transmission sends the raw 20-byte info_hash URL-encoded
raw_info_hash = bencode.encode(torrent_data['info'])  # This gives us the info part
binary_info_hash = hashlib.sha1(raw_info_hash).digest()  # This is the 20-byte binary

print(f"Binary info_hash: {binary_info_hash.hex()}")

# URL encode it
url_encoded_info_hash = quote(binary_info_hash)
print(f"URL encoded: {url_encoded_info_hash}")

# Build the announce URL
announce_url = f"http://127.0.0.1:8000/announce?info_hash={url_encoded_info_hash}&peer_id=-TR4000-testtesttest&port=51413&uploaded=0&downloaded=0&left=9772752&compact=1&event=started"

print(f"Full URL: {announce_url}")

# Make the request
try:
    response = requests.get(announce_url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.content}")
    print(f"Response as bencoded: {bencode.bdecode(response.content) if response.content else 'Empty'}")
except Exception as e:
    print(f"Error: {e}")
