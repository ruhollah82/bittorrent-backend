"""
Refactored BitTorrent Tracker Views

This module provides clean, maintainable tracker endpoints using the core tracker
logic inspired by webtorrent/bittorrent-tracker while maintaining Django integration.
"""
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@csrf_exempt
def announce(request):
    """
    BitTorrent Tracker Announce Endpoint

    Handles peer announcements for torrent swarms.
    Supports both GET and raw binary parsing for compatibility.
    """
    logger.error(f"DEBUG: Announce called, method={request.method}, query_string={request.META.get('QUERY_STRING')[:100]}")

    from .core.django_integration import tracker

    # For now, force raw parsing since Django parsing has issues with binary data
    try:
        raw_query = request.META.get('QUERY_STRING', '')
        if raw_query:
            logger.error(f"DEBUG: Using raw parsing, query: {raw_query[:100]}")
            return _handle_raw_announce(raw_query, request)
    except Exception as e:
        logger.error(f"DEBUG: Raw parsing failed: {e}")

    # Return error if parsing fails
    logger.error("DEBUG: Parsing failed")
    from .core.bencode import create_error_response, encode_response
    from django.http import HttpResponse
    response = create_error_response("Invalid request format")
    return HttpResponse(encode_response(response), content_type='text_plain')


def _handle_raw_announce(raw_query, request):
    """Handle announce with raw query string parsing"""
    from .core.django_integration import tracker
    from .core.common import bin_to_hex, parse_querystring
    from .core.bencode import create_error_response, encode_response
    from django.http import HttpResponse

    logger.error(f"DEBUG: Raw parsing started, query: {raw_query[:100]}")

    # Parse raw query string
    params = parse_querystring(raw_query)
    logger.error(f"DEBUG: Parsed params: {list(params.keys())}")

    # Validate and convert parameters
    try:
        # Info hash - should be binary data from raw parsing
        info_hash_raw = params.get('info_hash', '')
        if isinstance(info_hash_raw, str):
            try:
                # Try latin-1 encoding first
                if len(info_hash_raw) == 20:
                    binary_data = info_hash_raw.encode('latin-1')
                    params['info_hash'] = bin_to_hex(binary_data)
                else:
                    # If wrong length, try to interpret as hex or handle differently
                    params['info_hash'] = info_hash_raw
            except UnicodeEncodeError:
                # If latin-1 fails, the data might already be processed
                params['info_hash'] = info_hash_raw
        else:
            raise ValueError("Invalid info_hash")

        # Peer ID
        peer_id_raw = params.get('peer_id', '')
        if isinstance(peer_id_raw, str):
            try:
                if len(peer_id_raw) == 20:
                    binary_data = peer_id_raw.encode('latin-1')
                    params['peer_id'] = bin_to_hex(binary_data)
                else:
                    params['peer_id'] = peer_id_raw
            except UnicodeEncodeError:
                params['peer_id'] = peer_id_raw
        else:
            raise ValueError("Invalid peer_id")

        # Convert other parameters
        params['port'] = int(params.get('port', 0))
        params['uploaded'] = int(params.get('uploaded', 0))
        params['downloaded'] = int(params.get('downloaded', 0))
        params['left'] = int(params.get('left', 0))
        params['compact'] = int(params.get('compact', 0))
        params['event'] = params.get('event', 'update')
        params['numwant'] = min(int(params.get('numwant', 50)), 82)

        # Add metadata
        params['action'] = 1  # ANNOUNCE
        params['type'] = 'http'
        params['ip'] = request.META.get('REMOTE_ADDR', '127.0.0.1')
        params['addr'] = f"{params['ip']}:{params['port']}"

        # Look up torrent
        from torrents.models import Torrent
        torrent = Torrent.objects.filter(info_hash=params['info_hash']).first()

        # Handle with tracker
        response_data = tracker.server.handle_announce(params)

        # Update Django models
        tracker._update_django_models(None, torrent, params, response_data)

        # Create bencoded response
        from .core.bencode import create_announce_response
        response = create_announce_response(
            response_data['complete'],
            response_data['incomplete'],
            response_data['peers'],
            response_data['interval'],
            params.get('compact', 0) == 1
        )

        return HttpResponse(encode_response(response), content_type='text/plain')

    except Exception as e:
        logger.error(f"Raw announce parsing error: {e}")
        response = create_error_response("Internal server error")
        return HttpResponse(encode_response(response), content_type='text/plain')


@csrf_exempt
@require_GET
def scrape(request):
    """
    BitTorrent Tracker Scrape Endpoint

    Returns statistics for torrents.

    Query Parameters:
    - info_hash: SHA1 hash(es) of torrent(s) to scrape
    - auth_token: Authentication token (required)

    Returns:
        Bencoded response with torrent statistics
    """
    from .core.django_integration import tracker
    logger.debug(f"Scrape request from {request.META.get('REMOTE_ADDR')}: {request.GET}")
    return tracker.handle_scrape(request)


def stats(request):
    """
    Tracker Statistics Endpoint

    Returns current tracker statistics in JSON format.

    Returns:
        JSON response with tracker stats
    """
    import json
    from django.http import JsonResponse
    from .core.django_integration import tracker

    stats_data = tracker.get_stats()
    return JsonResponse(stats_data)
