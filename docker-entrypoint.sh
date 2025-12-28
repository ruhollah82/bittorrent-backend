#!/bin/bash
set -e

echo "Waiting for database..."
# Wait for database using Python (more reliable than netcat)
python << END
import sys
import time
import psycopg2
import os

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('DB_NAME', 'bittorrent_db'),
            user=os.environ.get('DB_USER', 'bittorrent_user'),
            password=os.environ.get('DB_PASSWORD', 'bittorrent_password'),
            host=os.environ.get('DB_HOST', 'db'),
            port=os.environ.get('DB_PORT', '5432')
        )
        conn.close()
        print("Database is ready!")
        sys.exit(0)
    except psycopg2.OperationalError:
        attempt += 1
        time.sleep(1)

print("Database connection failed after 30 attempts")
sys.exit(1)
END

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "=========================================="
echo "Checking for invite code..."
echo "=========================================="
# Create invite code if none exists
python << END
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import InviteCode
from django.utils import timezone
from django.db import models
from datetime import timedelta

# Check if there are any unused invite codes
unused_codes = InviteCode.objects.filter(
    is_active=True,
    used_by__isnull=True
).filter(
    models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
)

if unused_codes.exists():
    invite_code = unused_codes.first()
    print("")
    print("=" * 60)
    print("🎫 INVITE CODE FOR FIRST USER REGISTRATION")
    print("=" * 60)
    print("")
    print(f"   Code: {invite_code.code}")
    print(f"   Expires: {invite_code.expires_at.strftime('%Y-%m-%d %H:%M:%S') if invite_code.expires_at else 'Never'}")
    print("")
    print("   Use this code to register the first user at:")
    print("   http://localhost:8000/api/auth/register/")
    print("")
    print("=" * 60)
    print("")
else:
    # Create a new invite code
    invite_code = InviteCode.objects.create(
        created_by=None,
        expires_at=timezone.now() + timedelta(days=30),
        is_active=True
    )
    print("")
    print("=" * 60)
    print("🎫 INVITE CODE FOR FIRST USER REGISTRATION")
    print("=" * 60)
    print("")
    print(f"   Code: {invite_code.code}")
    print(f"   Expires: {invite_code.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    print("   Use this code to register the first user at:")
    print("   http://localhost:8000/api/auth/register/")
    print("")
    print("=" * 60)
    print("")
END

echo "Starting server..."
exec "$@"

