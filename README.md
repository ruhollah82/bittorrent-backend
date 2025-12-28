# 🌊 BitTorrent Private Tracker Backend

> **Empowering Peer-to-Peer File Sharing with Enterprise-Grade Security**

A comprehensive, production-ready BitTorrent private tracker backend built with Django REST Framework. Features advanced security, intelligent credit systems, real-time monitoring, and a complete API ecosystem for modern torrent management.

## ✨ **Features**

### 🎯 **Core Systems**

- **🔐 Authentication**: JWT tokens with invite-based registration
- **💰 Credit System**: Upload/download ratio tracking with user classes (Newbie → Elite)
- **📡 BitTorrent Tracker**: Full announce/scrape protocol implementation
- **🛡️ Security**: IP blocking, rate limiting, and suspicious activity monitoring
- **📊 Monitoring**: Comprehensive logging and real-time analytics
- **🎛️ Admin Panel**: User management and system configuration
- **📱 REST API**: Complete API with OpenAPI/Swagger documentation

### 🛠️ **Technology Stack**

- **Backend**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL (prod) / SQLite (dev)
- **Cache**: Redis for sessions and caching
- **Tasks**: Celery with Redis broker
- **Testing**: Comprehensive integration test suite (18 tests)
- **Documentation**: Interactive API docs with Swagger UI

## 📂 **Project Structure**

```
bittorrent-backend/
├── core/                    # Django settings and configuration
├── accounts/               # User authentication and profiles
├── api/                    # REST API routing
├── credits/                # Credit system and transactions
├── torrents/               # Torrent management
├── tracker/                # BitTorrent protocol endpoints
├── security/               # Security monitoring
├── admin_panel/           # Admin interface
├── logging_monitoring/    # System logs and monitoring
├── utils/                 # Helper utilities
├── venv/                  # Python virtual environment
├── db.sqlite3             # SQLite database (created)
├── .env                   # Environment variables (created)
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── integration_test.py    # Comprehensive test suite
├── setup_and_run.py       # Cross-platform setup script
├── setup_and_run.sh       # Unix setup script
├── setup_and_run.bat      # Windows setup script
├── SETUP_README.md        # Detailed setup guide
└── README.md              # This file
```

## 📚 **User Guides**

- **[BitTorrent Guide](./BITTORRENT_USER_GUIDE.md)**: Complete guide for creating, seeding, and downloading torrents
- **[Invite System](./INVITE_CODE_API_EXAMPLES.txt)**: How to generate and use invite codes

## 🚀 **Quick Start**

### ⚡ **Automated Setup (Recommended)**

Choose your platform and run the setup script:

#### **Linux/macOS**

```bash
# Download/clone the repository
git clone <repository-url>
cd bittorrent-backend

# Run automated setup
./setup_and_run.py
```

#### **Windows**

```cmd
# Download/clone the repository
git clone <repository-url>
cd bittorrent-backend

# Run automated setup
setup_and_run.bat
```

> **🎉 That's it!** The server will be running at `http://127.0.0.1:8000` with a default admin account.

### 📋 **Manual Setup (Alternative)**

For advanced users or custom configurations:

```bash
# Clone repository
git clone <repository-url>
cd bittorrent-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp env.example .env
# Edit .env as needed

# Database setup
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_admin

# Start server
python manage.py runserver
```

### 🧪 **Verify Installation**

Test your setup with the comprehensive test suite:

```bash
python integration_test.py
```

> **✅ All 18 tests should pass!**

## 🔗 **API Endpoints**

### 🔐 **Authentication**

```http
POST /api/auth/register/     # User registration with invite code
POST /api/auth/login/        # JWT token authentication
POST /api/auth/refresh/      # Token refresh
POST /api/auth/invite/create/ # Create invite codes (admin)
POST /api/auth/invite/generate/ # Generate invite codes (regular users)
GET  /api/auth/invite/my-codes/ # List user's invite codes & stats
```

### 👤 **User Management**

```http
GET  /api/user/profile/      # User profile
GET  /api/user/stats/        # User statistics
GET  /api/user/tokens/       # Auth tokens list
POST /api/user/tokens/       # Create auth token
```

### 📡 **BitTorrent Protocol**

```http
GET  /announce              # Tracker announce (BitTorrent protocol)
GET  /scrape               # Torrent statistics
```

### 💰 **Credits System**

```http
GET  /api/credits/balance/  # Credit balance
GET  /api/credits/transactions/ # Transaction history
GET  /api/credits/ratio-status/ # Upload/download ratio
```

### 📁 **Torrent Management**

```http
GET  /api/torrents/         # Torrent list
GET  /api/torrents/categories/ # Categories
GET  /api/torrents/popular/ # Popular torrents
GET  /api/torrents/my-torrents/ # User's torrents
POST /api/torrents/upload/  # Upload torrent (reactivates deleted torrents)
```

### 🛡️ **Security & Monitoring**

```http
GET  /api/security/stats/   # Security statistics
GET  /api/logs/health/      # System health check
```

### 📖 **API Documentation**

- **Swagger UI**: `http://127.0.0.1:8000/api/docs/`
- **OpenAPI Schema**: `http://127.0.0.1:8000/api/schema/`

## ⚙️ **Configuration**

### 📁 **Environment Setup**

The automated setup creates a `.env` file from `env.example`. Key settings:

```env
# Django Configuration
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver

# Database (SQLite for development, PostgreSQL for production)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Redis (optional for caching and sessions)
REDIS_URL=redis://127.0.0.1:6379/1

# BitTorrent Settings
TRACKER_ANNOUNCE_INTERVAL=1800
CREDIT_MULTIPLIER=1.0
```

### 🛠️ **Management Commands**

```bash
# Create invite codes for user registration
python manage.py create_invite --count 5 --expires 30

# Show available invite codes
python manage.py show_invite_codes --first-only  # Show first available code
python manage.py show_invite_codes               # Show all codes

# Setup admin panel and system configuration
python manage.py setup_admin

# Create superuser account
python manage.py createsuperuser

# Run database migrations
python manage.py migrate
```

### ⚡ **Background Tasks (Optional)**

```bash
# Start Celery worker
celery -A core worker --loglevel=info

# Start Celery beat scheduler
celery -A core beat --loglevel=info
```

## 🧪 **Testing**

### 🐳 **Docker Testing (Recommended)**

For Docker deployments, use the comprehensive test suite:

```bash
# 1. Setup test data (creates user, torrent, auth token)
docker-compose exec web python setup_test_data.py

# 2. Test all API endpoints
docker-compose exec web python test_api_comprehensive.py

# 3. Test tracker with seeder/leecher simulator
docker-compose exec web python test_tracker_simulator.py <info_hash> <auth_token>

# 4. Run complete Docker setup test
./test_docker_setup.sh
```

📖 **For detailed testing instructions, see [TESTING.md](./TESTING.md)**

### 📊 **Comprehensive Integration Tests**

Run the complete test suite covering all major functionality:

```bash
# Run all integration tests (18 tests covering complete user journey)
python integration_test.py

# Expected output: "Results: 18/18 tests passed"
```

**Test Coverage:**

- ✅ User registration and authentication
- ✅ Profile management and user stats
- ✅ Credit system and transactions
- ✅ BitTorrent tracker functionality
- ✅ Torrent management and categories
- ✅ Security monitoring
- ✅ API endpoints and error handling

### 🧬 **Django Unit Tests**

```bash
# Run Django's built-in test suite
python manage.py test

# Run specific app tests
python manage.py test accounts
python manage.py test torrents
```

### 🔬 **API Health Check**

```bash
# Quick health verification
curl http://127.0.0.1:8000/api/logs/health/

# Test authentication
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## 🔐 **Fortress Security: Advanced Protection Systems**

### 🛡️ **Multi-Layered Security Architecture**

- **🚦 Rate Limiting**: Intelligent abuse prevention with adaptive thresholds
- **🚫 IP Intelligence**: Automated suspicious IP detection and blocking
- **🎯 Anti-Cheat Engine**: Advanced fake upload/download detection algorithms
- **🔑 Cryptographic Tokens**: HMAC-signed tokens for tracker authentication
- **✅ Input Sanitization**: Comprehensive input validation and sanitization
- **🗃️ Database Security**: ORM-level SQL injection prevention
- **🌐 XSS Mitigation**: Automatic content sanitization and escaping

### 🏆 **Security Best Practices & Hardening**

- **🔒 HTTPS Enforcement**: Mandatory SSL/TLS encryption in production
- **🗝️ Secret Key Rotation**: Regular SECRET_KEY updates and secure storage
- **🌐 Host Restrictions**: Strict ALLOWED_HOSTS configuration
- **📊 Continuous Monitoring**: Real-time log analysis and anomaly detection
- **💾 Backup Strategy**: Automated database backups with encryption
- **🔄 Security Updates**: Regular dependency updates and vulnerability scanning

## 📈 **Observability Center: Real-Time Monitoring & Analytics**

### 📊 **Comprehensive Metrics Dashboard**

- **👥 User Activity**: Active users, registration trends, and engagement metrics
- **💰 Economic Indicators**: Credit transactions, ratio distributions, and economic health
- **🛡️ Security Intelligence**: Threat detection, blocked IPs, and security incidents
- **⚡ Performance Metrics**: System response times, throughput, and resource utilization
- **💾 Resource Monitoring**: Database performance, cache hit rates, and storage metrics

### 🚨 **Intelligent Alert System**

- **⚠️ Ratio Warnings**: Low ratio alerts with automated user notifications
- **🔍 Anomaly Detection**: Suspicious activity identification and automated responses
- **📈 Performance Alerts**: System bottleneck detection and scaling recommendations
- **🔒 Security Breach Alerts**: Real-time security incident notifications and responses

> **🎯 Insight**: Our monitoring system provides 360-degree visibility into your BitTorrent ecosystem!

## 🚀 **Production Deployment**

### 🏭 **Recommended Production Stack**

- **Database**: PostgreSQL with connection pooling
- **Application Server**: Gunicorn with 4+ workers
- **Reverse Proxy**: Nginx with SSL/TLS termination
- **Cache**: Redis cluster for sessions and caching
- **SSL**: Let's Encrypt with automatic renewal
- **Monitoring**: Health checks and logging
- **Backups**: Automated database backups

### 🐳 **Docker Deployment (Recommended)**

The easiest way to deploy the entire stack is using Docker Compose:

```bash
# Clone repository
git clone <repository-url>
cd bittorrent-backend

# Create environment file
cp env.example .env

# Start all services (Django, PostgreSQL, Redis, Celery)
docker-compose up -d

# Initialize database
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py setup_admin
```

**Services included:**
- **Django API Server** (port 8000)
- **PostgreSQL Database** (port 5432)
- **Redis Cache & Message Broker** (port 6379)
- **Celery Worker** (background tasks)
- **Celery Beat** (scheduled tasks)

**Access the application:**
- API Server: http://localhost:8000
- Admin Panel: http://localhost:8000/admin/
- API Docs: http://localhost:8000/api/docs/

📖 **For detailed Docker instructions, see [DOCKER_README.md](./DOCKER_README.md)**

### ⚙️ **Environment Variables for Production**

```env
DEBUG=False
SECRET_KEY=your-secure-production-key
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=django.db.backends.postgresql
# ... PostgreSQL and Redis configuration
```

## 📚 **Documentation**

### 📖 **API Documentation**

- **Swagger UI**: `http://127.0.0.1:8000/api/docs/`
- **OpenAPI Schema**: `http://127.0.0.1:8000/api/schema/`
- **Setup Guide**: See `SETUP_README.md` for detailed instructions
- **Docker Guide**: See `DOCKER_README.md` for Docker deployment instructions
- **Testing Guide**: See `TESTING.md` for comprehensive testing instructions

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python integration_test.py`
5. Submit a pull request

### 📋 **Development Standards**

- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting

## 📄 **License**

This project is licensed under the **MIT License** - see the LICENSE file for details.

---

**Built with Django REST Framework for the modern BitTorrent ecosystem** 🚀
