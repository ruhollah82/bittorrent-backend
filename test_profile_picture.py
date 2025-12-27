#!/usr/bin/env python
"""
Test script for profile picture upload functionality
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
import tempfile

def test_profile_picture_upload():
    """Test profile picture upload functionality"""

    # Create a test user
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

    # Create test client
    client = Client()

    # Login the user
    login_response = client.post('/api/auth/login/', {
        'username': 'testuser',
        'password': 'testpass123'
    })

    if login_response.status_code != 200:
        print("❌ Login failed")
        return False

    response_data = login_response.json()
    tokens = response_data['tokens']
    access_token = tokens['access']

    # Create a test image file
    from PIL import Image
    import io

    # Create a simple test image
    image = Image.new('RGB', (100, 100), color='red')
    image_io = io.BytesIO()
    image.save(image_io, format='JPEG')
    image_io.seek(0)

    # Create SimpleUploadedFile
    test_image = SimpleUploadedFile(
        name='test_profile.jpg',
        content=image_io.getvalue(),
        content_type='image/jpeg'
    )

    # Test profile picture upload
    headers = {
        'HTTP_AUTHORIZATION': f'Bearer {access_token}',
        'Content-Type': 'multipart/form-data'
    }
    upload_response = client.patch(
        '/api/user/profile/',
        {'profile_picture': test_image},
        **headers
    )

    print(f"Upload response status: {upload_response.status_code}")
    print(f"Upload response: {upload_response.content.decode()}")

    if upload_response.status_code == 200:
        response_data = upload_response.json()
        if 'profile_picture' in response_data and response_data['profile_picture']:
            print("✅ Profile picture upload successful!")
            print(f"Profile picture URL: {response_data['profile_picture']}")
            return True
        else:
            print("❌ Profile picture not returned in response")
            return False
    else:
        print(f"❌ Profile picture upload failed with status {upload_response.status_code}")
        return False

def test_invalid_file_upload():
    """Test uploading invalid file types"""

    # Create a test user
    user = User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123'
    )

    client = Client()

    # Login
    login_response = client.post('/api/auth/login/', {
        'username': 'testuser2',
        'password': 'testpass123'
    })

    response_data = login_response.json()
    tokens = response_data['tokens']
    access_token = tokens['access']

    # Create invalid file (text file)
    invalid_file = SimpleUploadedFile(
        name='test.txt',
        content=b'This is not an image',
        content_type='text/plain'
    )

    headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
    upload_response = client.patch(
        '/api/user/profile/',
        {'profile_picture': invalid_file},
        format='multipart',
        **headers
    )

    print(f"Invalid file upload status: {upload_response.status_code}")
    if upload_response.status_code == 400:
        print("✅ Invalid file properly rejected")
        return True
    else:
        print("❌ Invalid file was not rejected")
        return False

if __name__ == '__main__':
    print("Testing profile picture upload functionality...")

    # Clean up any existing test users
    User.objects.filter(username__in=['testuser', 'testuser2']).delete()

    try:
        # Test valid upload
        success1 = test_profile_picture_upload()

        # Test invalid upload
        success2 = test_invalid_file_upload()

        if success1 and success2:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed")

    finally:
        # Clean up test users
        User.objects.filter(username__in=['testuser', 'testuser2']).delete()
