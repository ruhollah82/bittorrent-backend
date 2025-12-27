# BitTorrent Backend - Quick Start Guide

This guide will help you set up and run the BitTorrent backend server from scratch on any platform.

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

#### Windows
Double-click `setup_and_run.bat` or run in Command Prompt:
```cmd
setup_and_run.bat
```

#### Linux/macOS
Choose your preferred method:

**Python script (recommended):**
```bash
./setup_and_run.py
```
or
```bash
python3 setup_and_run.py
```

**Shell script (alternative):**
```bash
./setup_and_run.sh
```

**Manual Python execution:**
```bash
python setup_and_run.py
```

### Option 2: Manual Setup

If the automated script doesn't work, follow these manual steps:

## 📋 Prerequisites

- **Python 3.8 or higher** (3.11+ recommended)
- **Git** (to clone the repository)
- **Internet connection** (for downloading dependencies)

### Check Python Version
```bash
python3 --version
# or on Windows
python --version
```

## 🛠️ Manual Setup Steps

### 1. Clone and Navigate
```bash
git clone <your-repo-url>
cd bittorrent-backend
```

### 2. Create Virtual Environment

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment
```bash
# Copy environment template
cp env.example .env

# Edit .env file with your settings (optional for development)
# nano .env  # or use your preferred editor
```

### 5. Database Setup
```bash
python manage.py migrate
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
# Follow prompts or use environment variables
```

### 7. Setup Admin Panel
```bash
python manage.py setup_admin
```

### 8. Create Invite Codes (Optional)
```bash
python manage.py create_invite --count 5 --expires 30 --created-by admin
```

### 9. Start Server
```bash
python manage.py runserver
```

## 🌐 Access Points

Once running, the server will be available at:

- **Main Site**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/api/docs/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Base**: http://127.0.0.1:8000/api/

## 🔐 Default Credentials

- **Username**: admin
- **Password**: admin123
- **Email**: admin@localhost

⚠️ **Change these credentials in production!**

## 🧪 Testing

Run the integration tests to verify everything works:

```bash
python integration_test.py
```

## 🏗️ Project Structure

```
bittorrent-backend/
├── accounts/           # User management
├── admin_panel/        # Admin interface
├── api/               # API configuration
├── core/              # Django settings
├── credits/           # Credit system
├── logging_monitoring/# Logging and monitoring
├── security/          # Security features
├── torrents/          # Torrent management
├── tracker/           # BitTorrent tracker
├── utils/             # Utilities
├── manage.py          # Django management script
├── requirements.txt   # Python dependencies
├── db.sqlite3         # SQLite database (created after setup)
├── venv/              # Virtual environment (created after setup)
├── .env               # Environment variables (created after setup)
├── .setup_complete    # Setup completion marker
├── setup_and_run.py   # Automated setup script (Python, cross-platform)
├── setup_and_run.sh   # Automated setup script (Shell, Unix-like)
├── setup_and_run.bat  # Automated setup script (Windows)
├── SETUP_README.md    # This setup guide
└── integration_test.py # Comprehensive test suite
```

## 🐛 Troubleshooting

### Common Issues

1. **Port 8000 already in use**
   ```bash
   # Find process using port 8000
   lsof -i :8000  # Linux/macOS
   netstat -ano | findstr :8000  # Windows

   # Kill the process or use different port
   python manage.py runserver 127.0.0.1:8001
   ```

2. **Python not found**
   - Install Python from https://python.org
   - Make sure it's in your PATH

3. **Permission denied**
   ```bash
   chmod +x setup_and_run.py
   ```

4. **Virtual environment issues**
   ```bash
   # Delete and recreate venv
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

5. **Database issues**
   ```bash
   rm db.sqlite3
   python manage.py migrate
   ```

### Redis/Celery (Optional)

For full functionality with background tasks:

```bash
# Install Redis
# Ubuntu/Debian: sudo apt install redis-server
# macOS: brew install redis
# Windows: Download from https://redis.io/download

# Start Redis
redis-server

# In another terminal, start Celery
celery -A core worker -l info

# In another terminal, start Celery Beat
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://127.0.0.1:8000/api/docs/
- **ReDoc**: http://127.0.0.1:8000/api/redoc/

## 🛡️ Production Deployment

For production deployment, see the main README.md for detailed instructions on:
- Using PostgreSQL instead of SQLite
- Setting up proper SSL/HTTPS
- Configuring reverse proxy (nginx)
- Environment variables
- Security hardening

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python integration_test.py`
4. Make your changes
5. Run tests again
6. Submit a pull request

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run the integration tests to verify setup
3. Check the logs in `logs/django.log`
4. Open an issue with error details
