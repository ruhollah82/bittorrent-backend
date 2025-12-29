# BitTorrent Tracker Refactoring

This directory contains a refactored BitTorrent tracker implementation based on the architecture of [webtorrent/bittorrent-tracker](https://github.com/webtorrent/bittorrent-tracker).

## Overview

The refactored tracker separates concerns into clean, maintainable modules:

- **Core Logic** (`tracker/core/`): Protocol-agnostic tracker implementation
- **Django Integration** (`tracker/views_new.py`): Django-specific endpoints and authentication
- **Tests** (`tracker/test_core.py`): Basic functionality tests

## Architecture

### Core Components

#### `tracker/core/common.py`
Constants and utilities shared across the tracker implementation.

#### `tracker/core/swarm.py`
Manages peers for a single torrent using an LRU cache with proper event handling.

#### `tracker/core/server.py`
Main tracker server that manages multiple torrent swarms.

#### `tracker/core/http_parser.py`
HTTP request parsing for BitTorrent tracker protocol.

#### `tracker/core/bencode.py`
Bencode encoding/decoding utilities for tracker responses.

#### `tracker/core/django_integration.py`
Django integration layer that combines core tracker logic with Django models and authentication.

### Key Improvements

1. **Clean Separation of Concerns**: Core tracker logic is separate from Django-specific code
2. **Proper Event Handling**: Based on webtorrent's event system (started, stopped, completed, update, paused)
3. **LRU Peer Management**: Efficient peer caching with automatic cleanup
4. **Compact Peer Lists**: Support for both compact and dictionary peer formats
5. **IPv6 Support**: Proper handling of IPv6 addresses
6. **Modular Design**: Easy to test and extend

## Usage

### New Views (Recommended)

```python
# tracker/views_new.py - Clean, maintainable implementation
from tracker.core.django_integration import tracker

@csrf_exempt
@require_GET
def announce(request):
    return tracker.handle_announce(request)

@csrf_exempt
@require_GET
def scrape(request):
    return tracker.handle_scrape(request)
```

### URL Configuration

```python
# urls.py
from tracker.views_new import announce, scrape, stats

urlpatterns = [
    path('announce', announce, name='tracker_announce'),
    path('scrape', scrape, name='tracker_scrape'),
    path('stats', stats, name='tracker_stats'),
]
```

## Testing

Run the core functionality tests:

```bash
cd /home/ruhollah/Projects/bittorrent-backend
python tracker/test_core.py
```

## Migration from Old Implementation

The old `tracker/views.py` (577 lines) has been replaced with:

- `tracker/core/` (6 clean modules, ~400 lines total)
- `tracker/views_new.py` (clean Django views, ~50 lines)
- `tracker/test_core.py` (tests, ~190 lines)

### Key Changes

1. **Removed Complex Logic**: Suspicious activity detection, rate limiting, and credit calculations moved to separate services
2. **Simplified Peer Management**: LRU cache instead of complex database queries
3. **Cleaner Event Handling**: Proper BitTorrent protocol event handling
4. **Better Error Handling**: Clear error messages and proper bencoding
5. **IPv6 Support**: Full IPv6 address handling
6. **Compact Responses**: Efficient binary peer lists

## Benefits

- **Maintainable**: Clean separation of concerns
- **Testable**: Core logic can be tested without Django
- **Scalable**: Efficient peer management with LRU caching
- **Standards Compliant**: Follows BitTorrent protocol properly
- **Extensible**: Easy to add new features or protocols

## Future Enhancements

- UDP tracker support
- WebSocket tracker support
- Multi-server clustering
- Advanced statistics and monitoring
- Plugin architecture for custom logic
