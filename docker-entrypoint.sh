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

echo "Starting server..."
exec "$@"

