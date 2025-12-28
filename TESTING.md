# 🧪 Testing Guide

Complete guide for testing the BitTorrent Tracker Backend APIs and tracker functionality.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [API Testing](#api-testing)
- [Tracker Testing](#tracker-testing)
- [Docker Testing](#docker-testing)
- [Manual Testing](#manual-testing)

## 🚀 Quick Start

### 1. Start Docker Containers

```bash
docker-compose up -d
```

### 2. Setup Test Data

```bash
docker-compose exec web python setup_test_data.py
```

This creates:
- Test user: `testuser` / `testpass123`
- Test torrent with info hash
- Auth token for tracker testing

### 3. Run Tests

```bash
# Test all APIs
docker-compose exec web python test_api_comprehensive.py

# Test tracker with seeder/leecher simulator
docker-compose exec web python test_tracker_simulator.py <info_hash> <auth_token>
```

## 📡 API Testing

### Comprehensive API Test

The `test_api_comprehensive.py` script tests all API endpoints:

```bash
# Run from Docker container
docker-compose exec web python test_api_comprehensive.py

# Run from host machine
python test_api_comprehensive.py http://localhost:8000
```

**What it tests:**
- ✅ Health check endpoint
- ✅ API documentation (Swagger, ReDoc, OpenAPI schema)
- ✅ User registration and authentication
- ✅ User profile and statistics
- ✅ Torrent management (list, categories, popular)
- ✅ Credit system (balance, transactions, ratio)
- ✅ Security monitoring
- ✅ Admin panel (if admin user)

**Output:**
- Colored terminal output (green = pass, red = fail)
- Detailed test results
- Summary statistics

### Example Output

```
Starting Comprehensive API Tests
Base URL: http://localhost:8000

============================================================
Health Check
============================================================
✅ PASS: Health check endpoint
   Details: Status: healthy

============================================================
Authentication Tests
============================================================
✅ PASS: User login
   Details: User: admin

============================================================
Test Summary
============================================================
Total Tests: 15
Passed: 14
Failed: 1
Success Rate: 93.3%
```

## 🌱 Tracker Testing (Seeder/Leecher Simulator)

### Basic Usage

```bash
# Get info hash and token from setup_test_data.py
python test_tracker_simulator.py <info_hash> <auth_token> [base_url]
```

### What it Tests

1. **Basic Announce Test**
   - Tests tracker announce endpoint
   - Verifies response format
   - Checks peer list

2. **Scrape Test**
   - Tests tracker scrape endpoint
   - Verifies torrent statistics
   - Checks seeder/leecher counts

3. **Seeder/Leecher Simulation**
   - Creates one seeder (has complete file)
   - Creates multiple leechers (downloading)
   - Simulates peer discovery
   - Tests download/upload progress

### Example

```bash
# Setup test data first
docker-compose exec web python setup_test_data.py

# Output will show:
# Info Hash: aabbccddeeff00112233445566778899aabbccdd
# Auth Token: abc123def456...

# Run simulator
python test_tracker_simulator.py \
  aabbccddeeff00112233445566778899aabbccdd \
  abc123def456... \
  http://localhost:8000
```

### Simulator Features

- **Realistic Peer IDs**: Generates valid BitTorrent peer IDs
- **Progress Simulation**: Simulates download/upload progress
- **Multiple Clients**: Can simulate multiple seeders/leechers
- **Threading**: Runs multiple clients concurrently
- **Colored Output**: Easy to read test results

### Example Output

```
BitTorrent Tracker Simulator
Base URL: http://localhost:8000
Info Hash: aabbccddeeff00112233445566778899aabbccdd

============================================================
Testing Basic Announce
============================================================
✅ Announce successful!
   Interval: 1800 seconds
   Min interval: 300 seconds
   Peers: 0

============================================================
Simulating Seeder and 2 Leechers
============================================================
🌱 Seeder created: -SE-abc123...
📥 Leecher 1 created: -LE-xyz789...
📥 Leecher 2 created: -LE-def456...
✅ Seeder connected to tracker
✅ Leecher 1 connected - Found 1 peers
✅ Leecher 2 connected - Found 2 peers

Simulating activity for 30 seconds...
[LEECH1] Progress: 33.3%
[LEECH2] Progress: 66.7%
✅ Simulation completed!
```

## 🐳 Docker Testing

### Comprehensive Docker Test

Run the complete Docker setup test:

```bash
./test_docker_setup.sh
```

**What it checks:**
- ✅ Docker and Docker Compose availability
- ✅ All containers running
- ✅ Database connectivity
- ✅ Redis connectivity
- ✅ Web server health
- ✅ API endpoint tests

### Test Individual Services

```bash
# Test database
docker-compose exec db pg_isready -U bittorrent_user

# Test Redis
docker-compose exec redis redis-cli ping

# Test web server
curl http://localhost:8000/api/logs/health/

# Check container logs
docker-compose logs -f web
docker-compose logs -f celery_worker
```

## 🔧 Manual Testing

### Using curl

#### 1. Health Check

```bash
curl http://localhost:8000/api/logs/health/
```

#### 2. User Login

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

#### 3. Get User Profile

```bash
# Replace TOKEN with actual access token from login
curl http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer TOKEN"
```

#### 4. Test Tracker Announce

```bash
# Replace INFO_HASH and TOKEN with actual values
curl "http://localhost:8000/announce?\
  info_hash=INFO_HASH&\
  peer_id=-qB0001-testpeerid12&\
  port=6881&\
  uploaded=0&\
  downloaded=0&\
  left=104857600&\
  compact=1&\
  event=started&\
  auth_token=TOKEN"
```

#### 5. Test Tracker Scrape

```bash
# Replace INFO_HASH and TOKEN
curl "http://localhost:8000/scrape?\
  info_hash=INFO_HASH&\
  auth_token=TOKEN"
```

### Using Python requests

```python
import requests
import bencode

BASE_URL = "http://localhost:8000"

# Login
response = requests.post(f"{BASE_URL}/api/auth/login/", json={
    "username": "testuser",
    "password": "testpass123"
})
token = response.json()["access"]

# Test announce
params = {
    "info_hash": "aabbccddeeff00112233445566778899aabbccdd",
    "peer_id": "-qB0001-testpeerid12",
    "port": "6881",
    "uploaded": "0",
    "downloaded": "0",
    "left": "104857600",
    "compact": "1",
    "event": "started",
    "auth_token": "YOUR_TOKEN"
}

response = requests.get(f"{BASE_URL}/announce", params=params)
data = bencode.decode(response.content)
print(data)
```

## 📊 Test Coverage

### API Endpoints Tested

- ✅ Authentication (`/api/auth/*`)
- ✅ User Management (`/api/user/*`)
- ✅ Torrent Management (`/api/torrents/*`)
- ✅ Credit System (`/api/credits/*`)
- ✅ Security (`/api/security/*`)
- ✅ Monitoring (`/api/logs/*`)
- ✅ Admin Panel (`/api/admin/*`)

### Tracker Endpoints Tested

- ✅ Announce (`/announce`)
- ✅ Scrape (`/scrape`)
- ✅ Peer Discovery
- ✅ Seeder/Leecher Simulation
- ✅ Download/Upload Progress
- ✅ Authentication Token Validation

## 🐛 Troubleshooting

### Tests Fail to Connect

1. **Check containers are running:**
   ```bash
   docker-compose ps
   ```

2. **Check web server is accessible:**
   ```bash
   curl http://localhost:8000/api/logs/health/
   ```

3. **Check logs:**
   ```bash
   docker-compose logs web
   ```

### Tracker Tests Fail

1. **Verify torrent exists:**
   ```bash
   docker-compose exec web python manage.py shell
   >>> from torrents.models import Torrent
   >>> Torrent.objects.all()
   ```

2. **Verify auth token is valid:**
   ```bash
   docker-compose exec web python manage.py shell
   >>> from accounts.models import AuthToken
   >>> AuthToken.objects.filter(is_active=True)
   ```

3. **Check tracker logs:**
   ```bash
   docker-compose logs web | grep announce
   ```

### API Tests Fail

1. **Create test user if needed:**
   ```bash
   docker-compose exec web python setup_test_data.py
   ```

2. **Check database migrations:**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Verify environment variables:**
   ```bash
   docker-compose exec web env | grep DB_
   ```

## 📝 Writing Custom Tests

### Example: Custom API Test

```python
import requests

BASE_URL = "http://localhost:8000"

def test_custom_endpoint():
    # Login
    response = requests.post(f"{BASE_URL}/api/auth/login/", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["access"]
    
    # Test endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/your-endpoint/", headers=headers)
    
    assert response.status_code == 200
    print("✅ Test passed!")
```

### Example: Custom Tracker Test

```python
import requests
import bencode

BASE_URL = "http://localhost:8000"

def test_custom_announce():
    params = {
        "info_hash": "YOUR_INFO_HASH",
        "peer_id": "-TEST-peerid12345678",
        "port": "6881",
        "uploaded": "0",
        "downloaded": "0",
        "left": "104857600",
        "compact": "1",
        "event": "started",
        "auth_token": "YOUR_TOKEN"
    }
    
    response = requests.get(f"{BASE_URL}/announce", params=params)
    data = bencode.decode(response.content)
    
    assert "interval" in data
    assert "peers" in data
    print("✅ Test passed!")
```

## 🎯 Best Practices

1. **Always setup test data first** using `setup_test_data.py`
2. **Run tests in Docker containers** for consistency
3. **Check logs** if tests fail
4. **Use colored output** scripts for better readability
5. **Test both authenticated and unauthenticated** endpoints
6. **Verify tracker responses** are properly bencoded
7. **Test edge cases** (invalid tokens, missing parameters, etc.)

---

**Need Help?** Check the main [README.md](./README.md) or [DOCKER_README.md](./DOCKER_README.md)

