# BitTorrent Tracker API Documentation

## Overview

This is a comprehensive BitTorrent tracker backend API built with Django REST Framework. The API provides complete functionality for user management, torrent tracking, credit systems, and administrative operations.

## API Documentation

The API is fully documented using OpenAPI 3.0 (Swagger) specifications and provides interactive documentation.

### Access Points

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Authentication Endpoints

#### Register User

```http
POST /api/auth/register/
```

**Request Body:**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "invite_code": "ABC123DEF"
}
```

**Response (201):**

```json
{
  "message": "کاربر با موفقیت ایجاد شد.",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "user_class": "newbie",
    "available_credit": "10.00"
  }
}
```

#### Login

```http
POST /api/auth/login/
```

**Request Body:**

```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response (200):**

```json
{
  "message": "ورود با موفقیت انجام شد.",
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  },
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

### Generate Invite Code (Regular Users)

```http
POST /api/auth/invite/generate/
Authorization: Bearer <token>
```

**Requirements:**
- User must have `member`, `trusted`, or `elite` user class
- User must have at least 5.00 credits available
- User can create maximum 2 invite codes per day

**Request Body:** (empty)

**Response (201 - Success):**

```json
{
  "code": "ABC123DEF456",
  "expires_at": "2025-01-03T17:36:49Z",
  "is_active": true
}
```

**Response (402 - Insufficient Credits):**

```json
{
  "error": "اعتبار کافی نیست",
  "required_credit": "5.00",
  "available_credit": "2.50",
  "shortage": "2.50"
}
```

**Response (403 - Insufficient User Class):**

```json
{
  "error": "دسترسی غیرمجاز",
  "message": "برای ایجاد کد دعوت نیاز به ارتقا کلاس کاربری به یکی از سطوح member, trusted, elite دارید",
  "current_class": "newbie"
}
```

**Response (429 - Daily Limit Exceeded):**

```json
{
  "error": "محدودیت روزانه",
  "message": "شما نمی‌توانید بیش از 2 کد دعوت در روز ایجاد کنید",
  "used_today": 2,
  "limit": 2
}
```

**Notes:**
- Generated invite codes expire after 7 days (shorter than admin codes)
- Costs 5.00 credits per invite code
- Credits are deducted immediately upon creation

## Core API Endpoints

### User Management

#### Get User Profile

```http
GET /api/user/profile/
Authorization: Bearer <token>
```

#### Update User Profile

```http
PATCH /api/user/profile/
Authorization: Bearer <token>
```

### Torrent Management

#### List Torrents

```http
GET /api/torrents/
Authorization: Bearer <token>
```

Query parameters:

- `category`: Filter by category
- `search`: Search by name/description

#### Get Torrent Details

```http
GET /api/torrents/{info_hash}/
Authorization: Bearer <token>
```

#### Upload Torrent

```http
POST /api/torrents/upload/
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

Form data:

- `torrent_file`: The .torrent file
- `name`: Custom name (optional)
- `description`: Description
- `category`: Category
- `is_private`: Boolean
- `tags`: Array of tags

#### Download Torrent

```http
GET /api/torrents/{info_hash}/download/
Authorization: Bearer <token> (for private torrents)
```

### BitTorrent Tracker Protocol

#### Announce (Core Tracker)

```http
GET /announce?info_hash={hash}&peer_id={id}&port={port}&uploaded={bytes}&downloaded={bytes}&left={bytes}&compact=1&event={event}&auth_token={token}
```

**Parameters:**

- `info_hash`: 40-character torrent hash
- `peer_id`: 20-character peer identifier
- `port`: Peer listening port
- `uploaded`: Bytes uploaded
- `downloaded`: Bytes downloaded
- `left`: Bytes remaining
- `compact`: Use compact peer list (1 or 0)
- `event`: started|completed|stopped
- `auth_token`: User authentication token

**Response (Bencoded):**

```
d8:intervali1800e12:min intervali300e5:peers6:peerdatae
```

#### Scrape (Torrent Statistics)

```http
GET /scrape?info_hash={hash}&auth_token={token}
```

**Response (Bencoded):**

```
d5:filesd40:info_hash40:completei2e10:downloadedi0e10:incompletei1eeee
```

### Credit System

#### Get Credit Balance

```http
GET /api/credits/balance/
Authorization: Bearer <token>
```

#### List Credit Transactions

```http
GET /api/credits/transactions/
Authorization: Bearer <token>
```

#### Check Download Permission

```http
POST /api/credits/check-download/
Authorization: Bearer <token>

{
    "torrent_id": 123
}
```

#### Lock Credits for Download

```http
POST /api/credits/lock-credit/
Authorization: Bearer <token>

{
    "torrent_id": 123
}
```

#### Complete Download Transaction

```http
POST /api/credits/complete-download/
Authorization: Bearer <token>

{
    "transaction_id": 456,
    "downloaded_bytes": 104857600
}
```

### Admin Panel (Admin Only)

#### Dashboard Analytics

```http
GET /api/admin/dashboard/
Authorization: Bearer <admin-token>
```

#### User Management

```http
GET /api/admin/users/
POST /api/admin/users/{id}/ (update user)
Authorization: Bearer <admin-token>
```

#### System Analytics

```http
GET /api/admin/analytics/
Authorization: Bearer <admin-token>
```

#### Bulk Torrent Moderation

```http
POST /api/admin/bulk-torrent-moderation/
Authorization: Bearer <admin-token>

{
    "action": "deactivate",
    "torrent_ids": [1, 2, 3],
    "reason": "Copyright violation"
}
```

#### System Cleanup

```http
POST /api/admin/cleanup/
Authorization: Bearer <admin-token>

{
    "cleanup_type": "logs",
    "days_old": 30
}
```

#### Performance Metrics

```http
GET /api/admin/performance-metrics/
Authorization: Bearer <admin-token>
```

## Data Models

### User

```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "user_class": "newbie|member|trusted|elite",
  "total_credit": "50.00",
  "locked_credit": "5.00",
  "available_credit": "45.00",
  "lifetime_upload": 104857600,
  "lifetime_download": 524288000,
  "ratio": 0.2,
  "download_multiplier": 0.5,
  "max_torrents": 1,
  "is_banned": false,
  "date_joined": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:30:00Z"
}
```

### Torrent

```json
{
  "id": 1,
  "info_hash": "aabbccddeeff00112233445566778899aabbccdd",
  "name": "Ubuntu 22.04 ISO",
  "description": "Ubuntu Linux distribution",
  "size": 3072000000,
  "files_count": 1,
  "created_by": {
    "id": 1,
    "username": "johndoe"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "is_active": true,
  "is_private": false,
  "category": "linux",
  "tags": ["ubuntu", "linux", "iso"],
  "size_gb": 3.07
}
```

### Credit Transaction

```json
{
  "id": 1,
  "user": 1,
  "torrent": 1,
  "transaction_type": "upload|download|bonus|penalty|admin_adjust",
  "amount": "10.50",
  "description": "Upload credit for torrent",
  "status": "completed|pending|failed|cancelled",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Responses

### Authentication Errors

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Validation Errors

```json
{
  "username": ["A user with that username already exists."],
  "invite_code": ["کد دعوت نامعتبر است."]
}
```

### Permission Errors

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Not Found Errors

```json
{
  "error": "Torrent not found"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- Anonymous users: 100 requests/hour
- Authenticated users: 1000 requests/hour

## File Upload Limits

- Maximum torrent file size: 10MB
- Supported formats: .torrent files only
- Automatic validation and parsing

## Credit System Rules

- **Upload Reward**: 1 credit per GB uploaded
- **Download Cost**: 1 credit per GB downloaded
- **Bonus Credits**: Awarded for various activities
- **User Classes**: Different multipliers and limits
  - Newbie: 0.5x multiplier, 1 max torrent
  - Member: 1.0x multiplier, 5 max torrents
  - Trusted: 1.5x multiplier, 15 max torrents
  - Elite: 2.0x multiplier, 50 max torrents

## Security Features

- JWT token authentication
- IP-based rate limiting
- Suspicious activity detection
- User banning system
- Private torrent access control
- Admin action logging

## Getting Started

1. **Register** a new user account with a valid invite code
2. **Login** to receive JWT tokens
3. **Upload** torrent files to earn credits
4. **Download** torrents using the tracker protocol
5. **Monitor** your activity and credit balance

## Development

The API documentation is automatically generated and updated. Access the interactive documentation at `/api/docs/` for testing endpoints directly in the browser.

All endpoints include comprehensive request/response examples and error handling documentation.
