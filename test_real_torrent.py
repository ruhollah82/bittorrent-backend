#!/usr/bin/env python3
"""
Test seeding and leeching with a real torrent file
"""
import sys
import os
import requests
import bencode
import hashlib
import secrets
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from accounts.models import User, InviteCode, AuthToken
from torrents.models import Torrent, Category, TorrentStats
from django.utils import timezone
from datetime import timedelta

def extract_torrent_info(torrent_path):
    """Extract info hash and details from torrent file"""
    with open(torrent_path, 'rb') as f:
        torrent_data = bencode.decode(f.read())
    
    # Handle different torrent formats
    info = None
    if b'info' in torrent_data:
        info = torrent_data[b'info']
    elif 'info' in torrent_data:
        info = torrent_data['info']
    else:
        # Try to find info dict
        for key, value in torrent_data.items():
            if isinstance(value, dict) and (b'name' in value or 'name' in value):
                info = value
                break
    
    if info is None:
        raise ValueError("Could not find 'info' dictionary in torrent file")
    
    # Get info hash
    info_bencoded = bencode.encode(info)
    info_hash = hashlib.sha1(info_bencoded).hexdigest()
    
    # Get name
    name_key = b'name' if b'name' in info else 'name'
    name = info[name_key]
    if isinstance(name, bytes):
        name = name.decode('utf-8', errors='ignore')
    
    # Get size
    size = 0
    if b'length' in info:
        size = info[b'length']
    elif 'length' in info:
        size = info['length']
    elif b'files' in info:
        size = sum(f.get(b'length', 0) for f in info[b'files'])
    elif 'files' in info:
        size = sum(f.get('length', 0) for f in info['files'])
    
    # Get announce
    announce = ''
    if b'announce' in torrent_data:
        announce = torrent_data[b'announce']
        if isinstance(announce, bytes):
            announce = announce.decode('utf-8', errors='ignore')
    elif 'announce' in torrent_data:
        announce = torrent_data['announce']
    
    return {
        'info_hash': info_hash,
        'name': name,
        'size': size,
        'announce': announce
    }

def create_test_user():
    """Create or get test user"""
    username = "seeder_user"
    email = "seeder@example.com"
    password = "seeder123"
    
    User = get_user_model()
    InviteCode = apps.get_model('accounts', 'InviteCode')
    
    # Get or create user
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'user_class': 'member'
        }
    )
    if created:
        user.set_password(password)
        # Create invite code for user
        invite_code = InviteCode.objects.create(
            code=secrets.token_urlsafe(12),
            expires_at=timezone.now() + timedelta(days=30),
            is_active=True
        )
        user.invite_code_used = invite_code
        user.save()
        print(f"✅ Created user: {username} / {password}")
    else:
        print(f"✅ Using existing user: {username}")
    
    return user

def create_auth_token(user):
    """Create auth token for user"""
    AuthToken = apps.get_model('accounts', 'AuthToken')
    token, created = AuthToken.objects.get_or_create(
        user=user,
        defaults={
            'token': secrets.token_urlsafe(32),
            'expires_at': timezone.now() + timedelta(days=30),
            'ip_bound': None
        }
    )
    if created:
        print(f"✅ Created auth token: {token.token}")
    else:
        print(f"✅ Using existing token: {token.token}")
    return token

def upload_torrent_to_server(torrent_info, user):
    """Upload torrent to server via API"""
    Torrent = apps.get_model('torrents', 'Torrent')
    Category = apps.get_model('torrents', 'Category')
    TorrentStats = apps.get_model('torrents', 'TorrentStats')
    
    # Check if torrent exists
    torrent = Torrent.objects.filter(info_hash=torrent_info['info_hash']).first()
    
    if torrent:
        print(f"✅ Torrent already exists: {torrent.name}")
        return torrent
    
    # Get or create category
    category, _ = Category.objects.get_or_create(
        name="Software",
        defaults={'slug': 'software'}
    )
    
    # Create torrent
    torrent = Torrent.objects.create(
        name=torrent_info['name'],
        info_hash=torrent_info['info_hash'],
        size=torrent_info['size'],
        category=category,
        created_by=user,
        is_private=True,
        announce_url="http://localhost:8000/announce"
    )
    
    TorrentStats.objects.create(torrent=torrent)
    print(f"✅ Created torrent: {torrent.name}")
    print(f"   Info Hash: {torrent.info_hash}")
    print(f"   Size: {torrent.size / (1024**3):.2f} GB")
    
    return torrent

def test_tracker_announce(info_hash, auth_token):
    """Test tracker announce"""
    import urllib.parse
    
    # Simulate seeder announce
    peer_id = secrets.token_hex(20)
    port = 6881
    uploaded = 0
    downloaded = 0
    left = 0  # Seeder (has all pieces)
    
    params = {
        'info_hash': bytes.fromhex(info_hash),
        'peer_id': bytes.fromhex(peer_id),
        'port': port,
        'uploaded': uploaded,
        'downloaded': downloaded,
        'left': left,
        'event': 'started',
        'compact': 1
    }
    
    url = f"http://localhost:8000/announce?{urllib.parse.urlencode({k: v if isinstance(v, (int, str)) else v.hex() for k, v in params.items()})}"
    
    headers = {
        'Authorization': f'Token {auth_token.token}'
    }
    
    print(f"\n🔍 Testing tracker announce...")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.content[:200]}")
            print("✅ Tracker announce successful!")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_real_torrent.py <torrent_file_path>")
        sys.exit(1)
    
    torrent_path = sys.argv[1]
    
    if not os.path.exists(torrent_path):
        print(f"Error: Torrent file not found: {torrent_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Testing Real Torrent Seeding/Leeching")
    print("=" * 60)
    
    # Extract torrent info
    print("\n📦 Extracting torrent information...")
    torrent_info = extract_torrent_info(torrent_path)
    print(f"   Name: {torrent_info['name']}")
    print(f"   Info Hash: {torrent_info['info_hash']}")
    print(f"   Size: {torrent_info['size'] / (1024**3):.2f} GB")
    
    # Create test user
    print("\n👤 Setting up test user...")
    from django.contrib.auth import get_user_model
    from django.apps import apps
    user = create_test_user()
    
    # Create auth token
    print("\n🔑 Creating auth token...")
    auth_token = create_auth_token(user)
    
    # Upload torrent to server
    print("\n📤 Uploading torrent to server...")
    torrent = upload_torrent_to_server(torrent_info, user)
    
    # Test tracker
    print("\n🌐 Testing tracker...")
    test_tracker_announce(torrent_info['info_hash'], auth_token)
    
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)
    print(f"\nYou can now test seeding/leeching with:")
    print(f"  Info Hash: {torrent_info['info_hash']}")
    print(f"  Auth Token: {auth_token.token}")
    print(f"\nRun tracker simulator:")
    print(f"  python test_tracker_simulator.py {torrent_info['info_hash']} {auth_token.token}")

