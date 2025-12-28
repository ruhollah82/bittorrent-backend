#!/usr/bin/env python3
"""
Setup Test Data for Docker Testing
Creates test user, torrent, and auth token for testing
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User, InviteCode, AuthToken
from torrents.models import Torrent, TorrentStats, Category
from django.utils import timezone
from datetime import timedelta
import hashlib
import secrets

def create_test_user():
    """Create a test user"""
    username = "testuser"
    email = "testuser@example.com"
    password = "testpass123"
    
    # Delete existing test user
    User.objects.filter(username=username).delete()
    
    # Create invite code if needed
    invite_code = InviteCode.objects.filter(used_by__isnull=True, is_active=True).first()
    if not invite_code:
        invite_code = InviteCode.objects.create(
            code=secrets.token_urlsafe(12),
            created_by=None,
            expires_at=timezone.now() + timedelta(days=30),
            is_active=True
        )
        print(f"Created invite code: {invite_code.code}")
    
    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        invite_code_used=invite_code
    )
    
    # Mark invite as used
    invite_code.used_by = user
    invite_code.save()
    
    print(f"✅ Created test user: {username} / {password}")
    return user

def create_test_torrent(user):
    """Create a test torrent"""
    # Generate a test info hash
    test_data = f"test_torrent_{timezone.now().timestamp()}"
    info_hash = hashlib.sha1(test_data.encode()).hexdigest()
    
    # Delete existing test torrent
    Torrent.objects.filter(info_hash=info_hash).delete()
    
    # Get or create a category
    category, _ = Category.objects.get_or_create(
        name="Test",
        defaults={"slug": "test", "description": "Test category"}
    )
    
    # Create torrent
    torrent = Torrent.objects.create(
        name="Test Torrent",
        info_hash=info_hash,
        size=100 * 1024 * 1024,  # 100MB
        files_count=1,
        piece_length=262144,  # 256KB
        created_by=user,
        category=category,
        is_private=True,
        is_active=True,
        description="Test torrent for tracker testing"
    )
    
    # Create torrent stats
    TorrentStats.objects.get_or_create(torrent=torrent)
    
    print(f"✅ Created test torrent: {torrent.name}")
    print(f"   Info Hash: {info_hash}")
    return torrent

def create_auth_token(user):
    """Create an auth token for the user"""
    # Delete existing tokens
    AuthToken.objects.filter(user=user).delete()
    
    # Create new token (token field is auto-generated)
    token = AuthToken.objects.create(
        user=user,
        token=secrets.token_urlsafe(32),  # Generate token
        expires_at=timezone.now() + timedelta(days=30),
        ip_bound=None
    )
    
    print(f"✅ Created auth token: {token.token}")
    return token

def main():
    """Main function"""
    print("Setting up test data...\n")
    
    try:
        # Create test user
        user = create_test_user()
        
        # Create test torrent
        torrent = create_test_torrent(user)
        
        # Create auth token
        token = create_auth_token(user)
        
        print("\n" + "="*60)
        print("Test Data Summary")
        print("="*60)
        print(f"Username: {user.username}")
        print(f"Password: testpass123")
        print(f"Email: {user.email}")
        print(f"\nTorrent Info Hash: {torrent.info_hash}")
        print(f"Torrent Name: {torrent.name}")
        print(f"Torrent Size: {torrent.size / (1024*1024):.2f} MB")
        print(f"\nAuth Token: {token.token}")
        print(f"Token Expires: {token.expires_at}")
        print("\n✅ Test data setup complete!")
        print("\nYou can now use these credentials for testing:")
        print(f"  python test_api_comprehensive.py")
        print(f"  python test_tracker_simulator.py {torrent.info_hash} {token.token}")
        
    except Exception as e:
        print(f"\n❌ Error setting up test data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

