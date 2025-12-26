# BitTorrent Private Tracker Backend

یک سیستم کامل BitTorrent tracker خصوصی با قابلیت‌های پیشرفته امنیتی و مدیریتی.

## 🚀 ویژگی‌ها

### ✅ کامل پیاده‌سازی شده
- **احراز هویت پیشرفته**: JWT + HMAC tokens برای tracker
- **سیستم Credit**: اقتصاد مبتنی بر آپلود/دانلود
- **Tracker API**: Announce/Scrape استاندارد BitTorrent
- **امنیت پیشرفته**: Anti-cheat، IP blocking، rate limiting
- **لاگ‌گیری کامل**: System logs، User activity، Alert system
- **پنل مدیریت**: Admin dashboard با آمار real-time
- **کلاس‌بندی کاربران**: Newbie، Member، Trusted، Elite

### 🔧 تکنولوژی‌ها
- **Backend**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Cache**: Redis
- **Task Queue**: Celery + Redis
- **Authentication**: JWT + HMAC
- **Documentation**: REST API با Swagger/OpenAPI

## 📁 ساختار پروژه

```
bittorrent-backend/
├── core/                    # تنظیمات اصلی Django
├── accounts/               # مدیریت کاربران و احراز هویت
├── tracker/                # API تراکر (announce/scrape)
├── credits/                # موتور credit و اقتصاد
├── torrents/               # مدیریت تورنت‌ها
├── security/               # امنیت و جلوگیری از تقلب
├── admin_panel/           # پنل مدیریت
├── logging_monitoring/    # لاگ‌گیری و مانیتورینگ
├── api/                   # API های REST
├── utils/                 # ابزارهای کمکی
└── venv/                  # محیط مجازی Python
```

## 🛠️ نصب و راه‌اندازی

### پیش‌نیازها
- Python 3.11+
- PostgreSQL (اختیاری، SQLite برای توسعه)
- Redis
- Git

### نصب

```bash
# کلون کردن پروژه
git clone <repository-url>
cd bittorrent-backend

# ایجاد محیط مجازی
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# یا venv\Scripts\activate در Windows

# نصب وابستگی‌ها
pip install -r requirements.txt

# تنظیمات اولیه
cp env.example .env
# فایل .env را با تنظیمات خود ویرایش کنید

# اجرای migration ها
python manage.py migrate

# ایجاد کاربر ادمین
python manage.py createsuperuser

# راه‌اندازی پنل ادمین
python manage.py setup_admin

# اجرای سرور
python manage.py runserver
```

## 🔑 API Endpoints

### Authentication
```http
POST /api/auth/register/     # ثبت‌نام با invite code
POST /api/auth/login/        # لاگین و دریافت JWT
POST /api/auth/refresh/      # refresh token
```

### User Management
```http
GET  /api/user/profile/      # پروفایل کاربر
GET  /api/user/stats/        # آمار کاربر
POST /api/user/tokens/       # مدیریت توکن‌های HMAC
```

### Tracker (BitTorrent Protocol)
```http
GET  /announce              # announce endpoint
GET  /scrape                # scrape endpoint
```

### Credits & Economy
```http
GET  /api/credits/balance/  # موجودی credit
GET  /api/credits/transactions/  # تاریخچه تراکنش‌ها
GET  /api/credits/user-classes/  # اطلاعات کلاس‌ها
```

### Torrents
```http
GET  /api/torrents/         # لیست تورنت‌ها
GET  /api/torrents/{hash}/  # جزئیات تورنت
GET  /api/torrents/popular/ # تورنت‌های محبوب
```

### Security
```http
GET  /api/security/stats/   # آمار امنیتی
GET  /api/security/suspicious-activities/  # فعالیت‌های مشکوک
GET  /api/security/announce-logs/  # لاگ announce
```

### Monitoring
```http
GET  /api/logs/dashboard/   # داشبورد مانیتورینگ
GET  /api/logs/system-logs/ # لاگ های سیستم
GET  /api/logs/health/      # بررسی سلامت سیستم
```

### Admin Panel
```http
GET  /api/admin/dashboard/  # داشبورد ادمین
GET  /api/admin/users/      # مدیریت کاربران
GET  /api/admin/system-config/  # تنظیمات سیستم
POST /api/admin/reports/generate/  # تولید گزارش
```

## ⚙️ تنظیمات مهم

### متغیرهای محیطی (.env)
```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=bittorrent_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# BitTorrent Settings
TRACKER_ANNOUNCE_INTERVAL=1800
MAX_TORRENTS_PER_USER=10
CREDIT_MULTIPLIER=1.0
MIN_RATIO_WARNING=0.5
```

### Management Commands
```bash
# ایجاد invite codes
python manage.py create_invite --count 10

# بروزرسانی آمار روزانه
python manage.py update_stats

# راه‌اندازی admin panel
python manage.py setup_admin
```

### Celery Tasks
```bash
# اجرای worker
celery -A core worker --loglevel=info

# اجرای beat scheduler
celery -A core beat --loglevel=info
```

## 🧪 تست

### اجرای تست‌ها
```bash
# اجرای همه تست‌ها
python manage.py test

# اجرای تست‌های خاص
python manage.py test accounts.tests
python manage.py test tracker.tests
python manage.py test security.tests
```

### تست API
```bash
# تست سلامت سیستم
curl http://localhost:8000/api/logs/health/

# تست لاگین
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'
```

## 🔐 امنیت

### ویژگی‌های امنیتی
- **Rate Limiting**: جلوگیری از abuse
- **IP Blocking**: مسدودی خودکار IP های مشکوک
- **Anti-Cheat**: تشخیص fake upload/download
- **Token Security**: HMAC tokens برای tracker
- **Input Validation**: اعتبارسنجی کامل ورودی‌ها
- **SQL Injection Protection**: استفاده از ORM Django
- **XSS Protection**: sanitization خودکار

### بهترین روش‌ها
- استفاده از HTTPS در production
- تغییر SECRET_KEY
- محدود کردن ALLOWED_HOSTS
- مانیتورینگ مداوم لاگ‌ها
- پشتیبان‌گیری منظم از database

## 📈 مانیتورینگ

### Metrics
- تعداد کاربران فعال
- تراکنش‌های credit
- فعالیت‌های امنیتی
- عملکرد سیستم
- استفاده از منابع

### Alerts
- Low ratio warnings
- Suspicious activities
- System performance issues
- Security breaches

## 🚀 Deployment

### Production Setup
```bash
# استفاده از PostgreSQL
# تنظیمات Gunicorn
# Nginx reverse proxy
# SSL certificate
# Redis برای cache و session
# Celery برای background tasks
# Log rotation
# Monitoring (Prometheus/Grafana)
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 📚 مستندات API

برای مستندات کامل API، پس از اجرای سرور به آدرس زیر بروید:
```
http://localhost:8000/swagger/  # اگر DRF-YASG نصب باشد
```

## 🤝 مشارکت

1. Fork پروژه
2. ایجاد branch برای ویژگی جدید
3. Commit تغییرات
4. Push و ایجاد Pull Request

### Coding Standards
- PEP 8 compliance
- کامنت‌گذاری مناسب
- تست‌های واحد
- مستندسازی API

## 📄 لایسنس

این پروژه تحت لایسنس MIT منتشر شده است.

## 📞 پشتیبانی

برای سوالات و مشکلات، issue جدید در GitHub ایجاد کنید.
