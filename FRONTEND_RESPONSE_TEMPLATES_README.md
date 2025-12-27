# Frontend Response Templates

This document provides comprehensive TypeScript and JavaScript templates for managing all API response bodies in your BitTorrent tracker frontend application.

## Overview

These templates are automatically generated from the OpenAPI schema and cover all response types that your frontend will encounter when interacting with the BitTorrent Tracker API.

## Files

- `frontend-response-templates.ts` - TypeScript interfaces and types
- `frontend-response-templates.js` - JavaScript objects and utilities
- `FRONTEND_RESPONSE_TEMPLATES_README.md` - This documentation

## Response Categories

### 🔐 Authentication Responses
- `UserProfile` - User profile data after registration/login
- `TokenResponse` - JWT tokens from login
- `TokenRefresh` - Refreshed JWT tokens
- `AuthToken` - API token management

### 👥 User Management Responses
- `UserManagement` - User data for admin panel
- `UserStats` - User statistics and metrics
- `UserActivity` - User activity logs

### 📁 Torrent Management Responses
- `Torrent` - Basic torrent information
- `TorrentDetail` - Detailed torrent information
- `TorrentStats` - Torrent statistics (seeders/leechers)

### 💰 Credit System Responses
- `CreditTransaction` - Credit transaction records

### ⚙️ Admin Panel Responses
- `AdminDashboard` - Admin dashboard statistics
- `SystemConfig` - System configuration settings
- `SystemStats` - System-wide statistics

### 📊 Monitoring Responses
- `SystemLog` - System log entries
- `AnnounceLog` - BitTorrent announce logs
- `SuspiciousActivity` - Suspicious activity reports
- `Alert` - Security alerts and notifications
- `IPBlock` - IP blocking records
- `InviteCodeManagement` - Invite code management

## Paginated Responses

All list endpoints return paginated responses with this structure:

```typescript
interface PaginatedResponse<T> {
  count: number;        // Total number of items
  next: string | null;  // URL for next page
  previous: string | null; // URL for previous page
  results: T[];         // Array of items
}
```

## TypeScript Usage

```typescript
import {
  UserProfile,
  PaginatedTorrents,
  Torrent,
  APIResponse
} from './frontend-response-templates';

// Type your API responses
const fetchUserProfile = async (): Promise<UserProfile> => {
  const response = await api.get('/api/user/profile/');
  return response.data;
};

const fetchTorrents = async (): Promise<PaginatedTorrents> => {
  const response = await api.get('/api/torrents/');
  return response.data;
};

// Use with generic API response wrapper
interface APIResponse<T> {
  data?: T;
  error?: APIError;
  success: boolean;
  message?: string;
}
```

## JavaScript Usage

```javascript
const { UserProfile, Torrent, isPaginatedResponse } = require('./frontend-response-templates');

// Use as template objects
const userProfile = { ...UserProfile };
const torrent = { ...Torrent };

// Validate responses
if (isPaginatedResponse(apiResponse)) {
  console.log(`Found ${apiResponse.count} items`);
}
```

## Enums and Constants

All enum values are provided as both TypeScript enums and JavaScript objects:

```typescript
// TypeScript
enum UserClassEnum {
  NEWBIE = 'newbie',
  MEMBER = 'member',
  TRUSTED = 'trusted',
  ELITE = 'elite'
}

// JavaScript
const UserClassEnum = {
  NEWBIE: 'newbie',
  MEMBER: 'member',
  TRUSTED: 'trusted',
  ELITE: 'elite'
};
```

## Utility Functions

### Type Guards
- `isPaginatedResponse(obj)` - Check if response is paginated
- `isAPIError(obj)` - Check if response contains an error

### Data Utilities
- `isUserBanned(user)` - Check if user account is banned
- `formatCredit(amount)` - Format credit amounts to 2 decimal places
- `calculateRatio(upload, download)` - Calculate upload/download ratio safely

## Error Handling

```typescript
interface APIError {
  detail?: string;
  [key: string]: any; // Field-specific errors
}

// Example error response
{
  "username": ["This field is required."],
  "email": ["Enter a valid email address."]
}
```

## Common Patterns

### 1. Handling Paginated Lists

```typescript
const fetchAllTorrents = async () => {
  let allTorrents: Torrent[] = [];
  let nextUrl: string | null = '/api/torrents/';

  while (nextUrl) {
    const response: PaginatedTorrents = await api.get(nextUrl);
    allTorrents = [...allTorrents, ...response.results];
    nextUrl = response.next;
  }

  return allTorrents;
};
```

### 2. User Authentication Flow

```typescript
const login = async (credentials: UserLoginRequest): Promise<TokenResponse> => {
  try {
    const response = await api.post('/api/auth/login/', credentials);
    const tokens: TokenResponse = response.data;

    // Store tokens
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);

    return tokens;
  } catch (error) {
    throw new Error('Login failed');
  }
};
```

### 3. Error Handling

```typescript
const handleAPIError = (error: any) => {
  if (isAPIError(error.response?.data)) {
    const apiError = error.response.data as APIError;

    if (apiError.detail) {
      showToast(apiError.detail);
    } else {
      // Handle field-specific errors
      Object.entries(apiError).forEach(([field, messages]) => {
        if (Array.isArray(messages)) {
          messages.forEach(message => showFieldError(field, message));
        }
      });
    }
  }
};
```

## API Endpoints Reference

### Authentication
- `POST /api/auth/register/` → `UserProfile`
- `POST /api/auth/login/` → `TokenResponse`
- `POST /api/auth/refresh/` → `TokenRefresh`

### User Management
- `GET /api/users/` → `PaginatedUserManagement`
- `GET /api/users/{id}/` → `UserManagement`
- `GET /api/users/stats/` → `UserStats`

### Torrents
- `GET /api/torrents/` → `PaginatedTorrents`
- `GET /api/torrents/{id}/` → `TorrentDetail`
- `GET /api/torrents/{id}/stats/` → `TorrentStats`

### Admin Panel
- `GET /api/admin/dashboard/` → `AdminDashboard`
- `GET /api/admin/config/` → `PaginatedSystemConfigs`
- `GET /api/admin/stats/` → `PaginatedSystemStats`

### Monitoring
- `GET /api/admin/logs/` → `PaginatedSystemLogs`
- `GET /api/admin/announce-logs/` → `PaginatedAnnounceLogs`
- `GET /api/admin/alerts/` → `PaginatedAlerts`
- `GET /api/admin/suspicious/` → `PaginatedSuspiciousActivities`

## Best Practices

1. **Type Safety**: Use TypeScript interfaces for compile-time type checking
2. **Error Handling**: Always check for API errors using the provided utilities
3. **Pagination**: Handle paginated responses properly for large datasets
4. **Data Validation**: Use the template objects to validate API responses
5. **Enum Usage**: Use the provided enums instead of hardcoded strings

## Integration with Frontend Frameworks

### React Example
```typescript
import React, { useState, useEffect } from 'react';
import { Torrent, PaginatedTorrents } from './frontend-response-templates';

const TorrentList: React.FC = () => {
  const [torrents, setTorrents] = useState<Torrent[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchTorrents = async () => {
      setLoading(true);
      try {
        const response: PaginatedTorrents = await api.get('/api/torrents/');
        setTorrents(response.results);
      } catch (error) {
        console.error('Failed to fetch torrents:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTorrents();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {torrents.map(torrent => (
        <div key={torrent.id}>
          <h3>{torrent.name}</h3>
          <p>Size: {torrent.size_formatted}</p>
          <p>Seeders: {torrent.seeders || 'N/A'}</p>
        </div>
      ))}
    </div>
  );
};
```

### Vue.js Example
```typescript
import { ref, onMounted } from 'vue';
import type { Torrent, PaginatedTorrents } from './frontend-response-templates';

export default {
  setup() {
    const torrents = ref<Torrent[]>([]);
    const loading = ref(false);

    const fetchTorrents = async () => {
      loading.value = true;
      try {
        const response: PaginatedTorrents = await api.get('/api/torrents/');
        torrents.value = response.results;
      } catch (error) {
        console.error('Failed to fetch torrents:', error);
      } finally {
        loading.value = false;
      }
    };

    onMounted(fetchTorrents);

    return {
      torrents,
      loading
    };
  }
};
```

## Updating Templates

When the API schema changes:

1. Regenerate the OpenAPI schema from your Django backend
2. Update the templates by re-running the generation script
3. Update your frontend code to handle any breaking changes
4. Test all API integrations thoroughly

## Support

These templates are automatically generated from your OpenAPI schema. For questions about specific endpoints or response formats, refer to the API documentation or contact the backend development team.
