#!/usr/bin/env python
"""
Simulate what transmission-cli does to test our tracker
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
binary_info_hash = hashlib.sha1(bencode.encode(torrent_data['info'])).digest()
url_encoded_info_hash = quote(binary_info_hash)

print(f"Binary info_hash: {binary_info_hash.hex()}")
print(f"URL encoded: {url_encoded_info_hash}")

# Simulate transmission-cli announce
announce_url = f"http://127.0.0.1:8000/announce?info_hash={url_encoded_info_hash}&peer_id=-TR4000-abcdefghijkl&port=51413&uploaded=0&downloaded=0&left=9772752&compact=1&event=started"

print(f"Making request to: {announce_url}")

response = requests.get(announce_url)
print(f"Status: {response.status_code}")
print(f"Response: {response.content}")

if response.content:
    try:
        decoded = bencode.bdecode(response.content)
        print(f"Decoded response: {decoded}")
    except Exception as e:
        print(f"Could not decode: {e}")
