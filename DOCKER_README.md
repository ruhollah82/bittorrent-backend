# 🐳 Docker Deployment Guide

Complete guide for deploying the BitTorrent Tracker Backend using Docker and Docker Compose.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Services Overview](#services-overview)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Ports and Endpoints](#ports-and-endpoints)
- [Common Operations](#common-operations)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)

### Install Docker

#### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

#### macOS
Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)

#### Windows
Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)

### Verify Installation
```bash
docker --version
docker-compose --version
```

## 🚀 Quick Start

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd bittorrent-backend
```

### 2. Create Environment File
```bash
cp env.example .env
```

Edit `.env` file with your configuration (optional for development):
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_NAME=bittorrent_db
DB_USER=bittorrent_user
DB_PASSWORD=bittorrent_password
```

### 3. Build and Start Services
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Initialize Database
```bash
# Create superuser
docker-compose exec web python manage.py createsuperuser

# Setup admin panel
docker-compose exec web python manage.py setup_admin

# Create invite codes (optional)
docker-compose exec web python manage.py create_invite --count 5
```

### 5. Access the Application

- **API Server**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation (Swagger)**: http://localhost:8000/api/docs/
- **API Documentation (ReDoc)**: http://localhost:8000/api/redoc/

## 🏗️ Services Overview

The Docker Compose setup includes the following services:

### 1. **Web** (Django Application)
- **Container**: `bittorrent_web`
- **Port**: `8000:8000`
- **Purpose**: Main Django REST API server
- **Endpoints**:
  - `/api/*` - REST API endpoints
  - `/announce` - BitTorrent tracker announce
  - `/scrape` - BitTorrent tracker scrape
  - `/admin/` - Django admin panel
  - `/api/docs/` - Swagger UI documentation

### 2. **Database** (PostgreSQL)
- **Container**: `bittorrent_db`
- **Port**: `5432:5432`
- **Image**: `postgres:16-alpine`
- **Purpose**: Primary database for all application data
- **Volumes**: `postgres_data` (persistent storage)

### 3. **Redis** (Cache & Message Broker)
- **Container**: `bittorrent_redis`
- **Port**: `6379:6379`
- **Image**: `redis:7-alpine`
- **Purpose**: 
  - Session storage
  - Cache backend
  - Celery message broker
  - Celery result backend
- **Volumes**: `redis_data` (persistent storage)

### 4. **Celery Worker**
- **Container**: `bittorrent_celery_worker`
- **Purpose**: Process background tasks
- **Tasks**: Credit calculations, statistics updates, periodic jobs

### 5. **Celery Beat**
- **Container**: `bittorrent_celery_beat`
- **Purpose**: Schedule periodic tasks
- **Tasks**: Scheduled statistics updates, cleanup jobs

## ⚙️ Configuration

### Environment Variables

All environment variables can be set in the `.env` file or directly in `docker-compose.yml`.

#### Django Settings
```env
DEBUG=True                          # Set to False in production
SECRET_KEY=your-secret-key          # Generate a secure key for production
ALLOWED_HOSTS=localhost,127.0.0.1  # Comma-separated list of allowed hosts
```

#### Database Configuration
```env
DB_NAME=bittorrent_db               # PostgreSQL database name
DB_USER=bittorrent_user             # PostgreSQL username
DB_PASSWORD=bittorrent_password     # PostgreSQL password
```

#### Redis Configuration
- Automatically configured to use the `redis` service
- Cache: `redis://redis:6379/1`
- Celery Broker: `redis://redis:6379/0`
- Celery Results: `redis://redis:6379/0`

#### CORS Settings
```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

#### BitTorrent Settings
```env
TRACKER_ANNOUNCE_INTERVAL=1800              # Announce interval in seconds (30 minutes)
MAX_TORRENTS_PER_USER=10                    # Maximum active torrents per user
CREDIT_MULTIPLIER=1.0                       # Credit multiplier for uploads
MIN_RATIO_WARNING=0.5                       # Minimum ratio for warning
MIN_RATIO_BAN=0.1                           # Minimum ratio before ban
FAKE_UPLOAD_DETECTION_THRESHOLD=0.1         # Fake upload detection threshold
MAX_ANNOUNCE_RATE=10                        # Maximum announces per minute
```

## 🔌 Ports and Endpoints

### Exposed Ports

| Service | Internal Port | External Port | Description |
|---------|--------------|---------------|-------------|
| Web | 8000 | 8000 | Django API server |
| PostgreSQL | 5432 | 5432 | Database |
| Redis | 6379 | 6379 | Cache and message broker |

### API Endpoints

#### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - JWT authentication
- `POST /api/auth/refresh/` - Token refresh

#### BitTorrent Tracker
- `GET /announce` - Tracker announce endpoint
- `GET /scrape` - Tracker scrape endpoint

#### User Management
- `GET /api/user/profile/` - User profile
- `GET /api/user/stats/` - User statistics

#### Torrent Management
- `GET /api/torrents/` - List torrents
- `POST /api/torrents/upload/` - Upload torrent

#### Credits
- `GET /api/credits/balance/` - Credit balance
- `GET /api/credits/transactions/` - Transaction history

#### Documentation
- `GET /api/docs/` - Swagger UI
- `GET /api/redoc/` - ReDoc documentation
- `GET /api/schema/` - OpenAPI schema

## 🛠️ Common Operations

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose stop
```

### Stop and Remove Containers
```bash
docker-compose down
```

### Stop and Remove Everything (Including Volumes)
```bash
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
```

### Execute Commands in Container
```bash
# Django management commands
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic

# Shell access
docker-compose exec web bash
docker-compose exec db psql -U bittorrent_user -d bittorrent_db
docker-compose exec redis redis-cli
```

### Rebuild After Code Changes
```bash
# Rebuild specific service
docker-compose build web

# Rebuild and restart
docker-compose up -d --build web
```

### Database Operations
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create migrations
docker-compose exec web python manage.py makemigrations

# Access database shell
docker-compose exec db psql -U bittorrent_user -d bittorrent_db
```

### Backup Database
```bash
# Create backup
docker-compose exec db pg_dump -U bittorrent_user bittorrent_db > backup.sql

# Restore backup
docker-compose exec -T db psql -U bittorrent_user bittorrent_db < backup.sql
```

### View Service Status
```bash
docker-compose ps
```

### Restart Specific Service
```bash
docker-compose restart web
docker-compose restart celery_worker
```

## 🚀 Production Deployment

### 1. Security Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Generate a strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Use strong database passwords
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Enable log rotation
- [ ] Review and restrict CORS origins

### 2. Production Environment Variables

Create a `.env.production` file:
```env
DEBUG=False
SECRET_KEY=<generate-strong-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=<strong-password>
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

### 3. Use Production-Ready Web Server

Update the `web` service in `docker-compose.yml` to use Gunicorn:

```yaml
web:
  command: >
    sh -c "python manage.py migrate &&
           python manage.py collectstatic --noinput &&
           gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4"
```

Add to `requirements.txt`:
```
gunicorn==21.2.0
```

### 4. Add Nginx Reverse Proxy

Create `nginx.conf`:
```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://django;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_redirect off;
    }

    location /static/ {
        alias /app/static/;
    }

    location /media/ {
        alias /app/media/;
    }
}
```

Add to `docker-compose.yml`:
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/conf.d/default.conf
    - static_volume:/app/static
    - media_volume:/app/media
  depends_on:
    - web
  networks:
    - bittorrent_network
```

### 5. Resource Limits

Add resource limits to `docker-compose.yml`:
```yaml
web:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

### 6. Health Checks

Health checks are already configured. Monitor with:
```bash
docker-compose ps
```

### 7. Backup Strategy

Set up automated backups:
```bash
# Add to crontab
0 2 * * * docker-compose exec -T db pg_dump -U bittorrent_user bittorrent_db | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

## 🧪 Testing

### Running Tests in Docker

#### 1. Setup Test Data

First, create test data (user, torrent, auth token):

```bash
docker-compose exec web python setup_test_data.py
```

This will create:
- Test user: `testuser` / `testpass123`
- Test torrent with info hash
- Auth token for tracker testing

#### 2. Test API Endpoints

Run comprehensive API tests:

```bash
# Test all API endpoints
docker-compose exec web python test_api_comprehensive.py

# Or test from host machine
python test_api_comprehensive.py http://localhost:8000
```

The test script will:
- ✅ Test health check endpoint
- ✅ Test API documentation endpoints
- ✅ Test authentication (login/register)
- ✅ Test user management endpoints
- ✅ Test torrent management endpoints
- ✅ Test credit system endpoints
- ✅ Test security monitoring endpoints
- ✅ Test admin panel endpoints

#### 3. Test Tracker (Seeder/Leecher Simulator)

Test the BitTorrent tracker with fake seeder and leecher:

```bash
# Get info hash and token from setup_test_data.py output
# Then run simulator
docker-compose exec web python test_tracker_simulator.py <info_hash> <auth_token>

# Or from host machine
python test_tracker_simulator.py <info_hash> <auth_token> http://localhost:8000
```

The simulator will:
- ✅ Test basic announce functionality
- ✅ Test scrape functionality
- ✅ Simulate one seeder and multiple leechers
- ✅ Test peer discovery
- ✅ Test download/upload simulation

**Example:**
```bash
# After running setup_test_data.py, you'll get:
# Info Hash: aabbccddeeff00112233445566778899aabbccdd
# Auth Token: abc123...

# Run simulator
python test_tracker_simulator.py aabbccddeeff00112233445566778899aabbccdd abc123...
```

#### 4. Comprehensive Docker Test

Run the complete Docker setup test:

```bash
./test_docker_setup.sh
```

This script will:
- ✅ Check Docker and Docker Compose
- ✅ Verify all containers are running
- ✅ Test database connection
- ✅ Test Redis connection
- ✅ Test web server health
- ✅ Run API tests

### Test Results

All test scripts provide colored output:
- 🟢 **Green** = Test passed
- 🔴 **Red** = Test failed
- 🟡 **Yellow** = Warning/Info
- 🔵 **Blue** = Details

### Manual Testing

You can also test manually using curl:

```bash
# Health check
curl http://localhost:8000/api/logs/health/

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Get user profile (replace TOKEN with actual token)
curl http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer TOKEN"

# Test tracker announce (replace INFO_HASH and TOKEN)
curl "http://localhost:8000/announce?info_hash=INFO_HASH&peer_id=-qB0001-testpeerid12&port=6881&uploaded=0&downloaded=0&left=104857600&compact=1&event=started&auth_token=TOKEN"
```

## 🔍 Troubleshooting

### Services Won't Start

1. **Check logs**:
   ```bash
   docker-compose logs
   ```

2. **Check port conflicts**:
   ```bash
   # Linux
   sudo netstat -tulpn | grep :8000
   
   # macOS
   lsof -i :8000
   ```

3. **Rebuild containers**:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Database Connection Issues

1. **Verify database is healthy**:
   ```bash
   docker-compose ps db
   ```

2. **Check database logs**:
   ```bash
   docker-compose logs db
   ```

3. **Test connection**:
   ```bash
   docker-compose exec web python manage.py dbshell
   ```

### Redis Connection Issues

1. **Check Redis is running**:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

2. **View Redis logs**:
   ```bash
   docker-compose logs redis
   ```

### Celery Not Processing Tasks

1. **Check worker logs**:
   ```bash
   docker-compose logs celery_worker
   ```

2. **Restart worker**:
   ```bash
   docker-compose restart celery_worker
   ```

3. **Check Redis connection**:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

### Static Files Not Loading

1. **Collect static files**:
   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

2. **Check volume mounts**:
   ```bash
   docker-compose exec web ls -la /app/static
   ```

### Permission Issues

1. **Fix file permissions**:
   ```bash
   sudo chown -R $USER:$USER .
   ```

2. **Check volume permissions**:
   ```bash
   docker-compose exec web ls -la /app/media
   ```

### Out of Memory

1. **Check container resources**:
   ```bash
   docker stats
   ```

2. **Increase Docker memory limit** (Docker Desktop → Settings → Resources)

3. **Add resource limits** to `docker-compose.yml`

### Database Migrations Failing

1. **Check migration status**:
   ```bash
   docker-compose exec web python manage.py showmigrations
   ```

2. **Reset migrations** (⚠️ **WARNING**: This will delete data):
   ```bash
   docker-compose down -v
   docker-compose up -d
   docker-compose exec web python manage.py migrate
   ```

## 📊 Monitoring

### View Resource Usage
```bash
docker stats
```

### View Service Health
```bash
docker-compose ps
```

### Check Logs
```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

## 🔄 Updates and Maintenance

### Update Application Code
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

### Update Dependencies
```bash
# Edit requirements.txt
# Rebuild
docker-compose build --no-cache web
docker-compose up -d
```

### Clean Up
```bash
# Remove unused images
docker image prune

# Remove unused volumes (⚠️ **WARNING**: May delete data)
docker volume prune

# Full cleanup
docker system prune -a
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Redis Docker Image](https://hub.docker.com/_/redis)

---

**Need Help?** Check the main [README.md](./README.md) or open an issue on GitHub.

