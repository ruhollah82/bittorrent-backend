"""
Django integration layer for the BitTorrent tracker
"""
import logging
from typing import Optional, Dict, Any
from django.http import HttpResponse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .server import TrackerServer
from .http_parser import parse_http_request
from .bencode import (
    encode_response, create_announce_response,
    create_scrape_response, create_error_response
)
from .common import ACTIONS, bin_to_hex, DEFAULT_ANNOUNCE_PEERS, MAX_ANNOUNCE_PEERS
from security.models import AnnounceLog
from torrents.models import Torrent, Peer
from accounts.models import User, AuthToken

logger = logging.getLogger(__name__)


class DjangoTracker:
    """
    Django-integrated BitTorrent tracker that uses the core tracker logic
    while maintaining compatibility with Django models and authentication
    """

    def __init__(self):
        self.tracker_settings = getattr(settings, 'BITTORRENT_SETTINGS', {})

        # Initialize core tracker server with protocol support
        self.server = TrackerServer(
            interval_ms=self.tracker_settings.get('TRACKER_ANNOUNCE_INTERVAL', 600) * 1000,
            peers_cache_length=self.tracker_settings.get('MAX_PEERS_PER_SWARM', 1000),
            peers_cache_ttl=self.tracker_settings.get('PEER_TTL_SECONDS', 1200) * 1000,
            http=self.tracker_settings.get('HTTP_ENABLED', True),
            udp=self.tracker_settings.get('UDP_ENABLED', True),
            ws=self.tracker_settings.get('WS_ENABLED', True)
        )

        # Set up filtering based on Django models
        self.server.set_filter(self._torrent_filter)

    def _torrent_filter(self, info_hash: str, params: dict) -> bool:
        """
        Filter function that checks if torrent exists and is active

        Args:
            info_hash: Torrent info hash
            params: Request parameters

        Returns:
            True if torrent is allowed
        """
        try:
            torrent = Torrent.objects.get(info_hash=info_hash, is_active=True)
            return True
        except Torrent.DoesNotExist:
            return False

    def handle_announce(self, request) -> HttpResponse:
        """
        Handle announce request with Django integration

        Args:
            request: Django HttpRequest

        Returns:
            HttpResponse with bencoded data
        """
        try:
            # Parse parameters from Django's parsed request
            params = self._parse_django_request(request)

            print(f"DEBUG: Announce - parsed info_hash: {params.get('info_hash')}, url: {request.get_full_path()}")

            # Validate and enhance parameters
            validation_result = self._validate_announce_params(params, request)
            if not validation_result['valid']:
                return self._error_response(validation_result['error'])

            # Check authentication if required
            user = None
            torrent = validation_result['torrent']
            if torrent.is_private:
                auth_result = self._validate_auth_token(request, params['info_hash'])
                if not auth_result['valid']:
                    return self._error_response(auth_result['error'])
                user = auth_result['user']

                # Check user permissions
                perm_result = self._check_user_permissions(user, torrent, params)
                if not perm_result['allowed']:
                    return self._error_response(perm_result['error'])

            # Handle the announce with core tracker
            params['user'] = user
            params['torrent'] = torrent

            with transaction.atomic():
                response_data = self.server.handle_announce(params)

                # Update Django models
                self._update_django_models(user, torrent, params, response_data)

                # Create announce response
                compact = params.get('compact', 0) == 1
                response = create_announce_response(
                    response_data['complete'],
                    response_data['incomplete'],
                    response_data['peers'],
                    response_data['interval'],
                    compact
                )

            return HttpResponse(encode_response(response), content_type='text/plain')

        except Exception as e:
            logger.error(f"Announce error: {e}", exc_info=True)
            return self._error_response("Internal server error")

    def handle_scrape(self, request) -> HttpResponse:
        """
        Handle scrape request with Django integration

        Args:
            request: Django HttpRequest

        Returns:
            HttpResponse with bencoded data
        """
        try:
            # Parse HTTP request
            params = parse_http_request(
                request.get_full_path(),
                dict(request.headers),
                self._get_client_ip(request),
                trust_proxy=self.tracker_settings.get('TRUST_PROXY', False)
            )

            # Validate authentication for scrape
            auth_result = self._validate_auth_token(request, None)
            if not auth_result['valid']:
                return self._error_response(auth_result['error'])

            # Handle scrape with core tracker
            response_data = self.server.handle_scrape(params)

            # Filter results to only include torrents the user has access to
            user = auth_result['user']
            filtered_files = {}
            for info_hash, stats in response_data['files'].items():
                try:
                    torrent = Torrent.objects.get(info_hash=info_hash.lower())
                    if not torrent.is_private or torrent.created_by == user:
                        filtered_files[info_hash] = stats
                except Torrent.DoesNotExist:
                    continue

            response = create_scrape_response(filtered_files)
            return HttpResponse(encode_response(response), content_type='text/plain')

        except Exception as e:
            logger.error(f"Scrape error: {e}", exc_info=True)
            return self._error_response("Internal server error")

    def _validate_announce_params(self, params: dict, request) -> dict:
        """Validate announce parameters and get torrent"""
        try:
            info_hash = params['info_hash'].lower()
            torrent = Torrent.objects.get(info_hash=info_hash, is_active=True)
            return {'valid': True, 'torrent': torrent}
        except Torrent.DoesNotExist:
            return {'valid': False, 'error': 'Torrent not found'}
        except KeyError:
            return {'valid': False, 'error': 'Missing info_hash'}

    def _validate_auth_token(self, request, info_hash: str = None) -> dict:
        """Validate authentication token"""
        auth_token = request.GET.get('auth_token')
        if not auth_token:
            return {'valid': False, 'error': 'Missing auth_token'}

        try:
            token = AuthToken.objects.get(token=auth_token, is_active=True)
        except AuthToken.DoesNotExist:
            return {'valid': False, 'error': 'Invalid auth_token'}

        if token.is_expired():
            return {'valid': False, 'error': 'Expired auth_token'}

        # IP binding check
        client_ip = self._get_client_ip(request)
        if token.ip_bound and token.ip_bound != client_ip:
            return {'valid': False, 'error': 'IP address mismatch'}

        token.last_used = timezone.now()
        token.save(update_fields=['last_used'])

        return {'valid': True, 'user': token.user}

    def _check_user_permissions(self, user, torrent, params) -> dict:
        """Check if user has permission to access the torrent"""
        # Check if user is banned
        if user.is_banned:
            return {'allowed': False, 'error': 'User banned'}

        # Check torrent ownership for private torrents
        if torrent.created_by != user:
            # Check credit requirements
            torrent_size_gb = torrent.size / (1024 ** 3)
            required_credit = torrent_size_gb

            if user.available_credit < required_credit:
                return {
                    'allowed': False,
                    'error': f'Insufficient credit. Required: {required_credit:.2f} GB, Available: {user.available_credit:.2f} GB'
                }

            # Check torrent limits
            active_torrents = user.peers.filter(state__in=['started', 'completed']).count()
            if active_torrents >= user.max_torrents:
                return {
                    'allowed': False,
                    'error': f'Maximum torrents reached. Current: {active_torrents}, Max: {user.max_torrents}'
                }

        return {'allowed': True}

    def _parse_django_request(self, request):
        """Parse Django HTTP request into tracker parameters"""
        params = {}

        # Get action from URL path
        path = request.path
        if path == '/announce':
            params['action'] = ACTIONS['ANNOUNCE']
        elif path == '/scrape':
            params['action'] = ACTIONS['SCRAPE']
        else:
            raise ValueError(f"Invalid path: {path}")

        # Set protocol type
        params['type'] = 'http'

        # Get client IP
        params['ip'] = self._get_client_ip(request)

        # Parse announce parameters
        if params['action'] == ACTIONS['ANNOUNCE']:
            # Info hash - Django has already URL-decoded it to binary string
            info_hash_raw = request.GET.get('info_hash', '')
            print(f"DEBUG: Raw info_hash: {repr(info_hash_raw)}, len: {len(info_hash_raw)}")
            if isinstance(info_hash_raw, str) and len(info_hash_raw) >= 19:  # Allow some tolerance
                # Pad or truncate to 20 bytes if needed
                if len(info_hash_raw) < 20:
                    info_hash_raw += '\x00' * (20 - len(info_hash_raw))
                elif len(info_hash_raw) > 20:
                    info_hash_raw = info_hash_raw[:20]
                params['info_hash'] = bin_to_hex(info_hash_raw.encode('latin-1'))
            else:
                raise ValueError(f"Invalid info_hash length: {len(info_hash_raw)}")

            # Peer ID
            peer_id_raw = request.GET.get('peer_id', '')
            if isinstance(peer_id_raw, str) and len(peer_id_raw) == 20:
                params['peer_id'] = bin_to_hex(peer_id_raw.encode('latin-1'))
            else:
                raise ValueError("Invalid peer_id")

            # Other parameters
            params['port'] = int(request.GET.get('port', 0))
            params['uploaded'] = int(request.GET.get('uploaded', 0))
            params['downloaded'] = int(request.GET.get('downloaded', 0))
            params['left'] = int(request.GET.get('left', 0))
            params['compact'] = int(request.GET.get('compact', 0))
            params['event'] = request.GET.get('event', 'update')
            params['numwant'] = min(int(request.GET.get('numwant', DEFAULT_ANNOUNCE_PEERS)), MAX_ANNOUNCE_PEERS)

            # Generate address
            params['addr'] = f"{params['ip']}:{params['port']}"

        elif params['action'] == ACTIONS['SCRAPE']:
            # Info hash for scrape
            info_hash_raw = request.GET.get('info_hash')
            if info_hash_raw:
                if isinstance(info_hash_raw, str):
                    info_hash_raw = [info_hash_raw]
                params['info_hash'] = []
                for ih in info_hash_raw:
                    if isinstance(ih, str) and len(ih) == 20:
                        params['info_hash'].append(bin_to_hex(ih.encode('latin-1')))
                    else:
                        raise ValueError("Invalid info_hash in scrape")

        return params

    def _update_django_models(self, user, torrent, params, response_data):
        """Update Django models based on announce data"""
        # For public torrents, track anonymous peers too
        if not user and torrent.is_private:
            return  # Skip for anonymous users on private torrents


        # Create/update Peer model
        peer_addr = f"{params['ip']}:{params['port']}"

        if user:
            # For authenticated users
            peer, created = Peer.objects.get_or_create(
                torrent=torrent,
                user=user,
                defaults={
                    'peer_id': params['peer_id'],
                    'ip_address': params['ip'],
                    'port': params['port'],
                    'uploaded': params.get('uploaded', 0),
                    'downloaded': params.get('downloaded', 0),
                    'left': params.get('left', 0),
                    'state': params.get('event', 'started'),
                    'is_seeder': params.get('left', 0) == 0,
                    'user_agent': params.get('user_agent', ''),
                }
            )
        else:
            # For anonymous users on public torrents
            # Use peer_id as unique identifier since we don't have user
            peer, created = Peer.objects.get_or_create(
                torrent=torrent,
                peer_id=params['peer_id'],
                defaults={
                    'user': None,
                    'ip_address': params['ip'],
                    'port': params['port'],
                    'uploaded': params.get('uploaded', 0),
                    'downloaded': params.get('downloaded', 0),
                    'left': params.get('left', 0),
                    'state': params.get('event', 'started'),
                    'is_seeder': params.get('left', 0) == 0,
                    'user_agent': params.get('user_agent', ''),
                }
            )

        if not created:
            # Update existing peer
            peer.uploaded = params.get('uploaded', peer.uploaded)
            peer.downloaded = params.get('downloaded', peer.downloaded)
            peer.left = params.get('left', peer.left)
            peer.state = params.get('event', peer.state)
            peer.is_seeder = params.get('left', 0) == 0
            peer.last_announced = timezone.now()
            peer.save()

        # Create announce log (only for authenticated users to avoid spam)
        if user:
            AnnounceLog.objects.create(
                user=user,
                torrent=torrent,
                event=params.get('event', 'update'),
                uploaded=params.get('uploaded', 0),
                downloaded=params.get('downloaded', 0),
                left=params.get('left', 0),
                ip_address=params['ip'],
                port=params['port'],
                peer_id=params['peer_id'],
                user_agent=params.get('user_agent', ''),
            )

    def _get_client_ip(self, request) -> str:
        """Get client IP address from Django request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def handle_udp_request(self, data: bytes, address: tuple) -> Optional[bytes]:
        """
        Handle UDP tracker request

        Args:
            data: Raw UDP packet data
            address: (host, port) tuple

        Returns:
            Response packet data or None
        """
        try:
            # Parse UDP request
            params = self.server.udp_parser.parse_request(data, address)
            if not params:
                return None

            # Validate torrent and authentication for announce/scrape
            if params['action'] in [ACTIONS['ANNOUNCE'], ACTIONS['SCRAPE']]:
                validation_result = self._validate_udp_params(params)
                if not validation_result['valid']:
                    # Return error response
                    transaction_id = params.get('transaction_id', 0)
                    return self.server.udp_parser.create_error_response(
                        transaction_id, validation_result['error']
                    )

                params.update(validation_result)

            # Handle with core server
            return self.server.handle_udp_request(data, address)

        except Exception as e:
            logger.error(f"UDP request error: {e}")
            return None

    def handle_websocket_request(self, socket, message: str, headers: dict = None) -> Optional[str]:
        """
        Handle WebSocket tracker request

        Args:
            socket: WebSocket connection object
            message: JSON message string
            headers: HTTP headers dictionary

        Returns:
            JSON response string or None
        """
        try:
            # Parse WebSocket request
            opts = {
                'trustProxy': self.tracker_settings.get('TRUST_PROXY', False),
                'headers': headers or {},
                'remote_addr': getattr(socket, 'remote_address', None)
            }

            params = self.server.ws_parser.parse_request(socket, message, opts)
            if not params:
                return None

            # Validate torrent and authentication
            if params['action'] in ['announce', 'scrape']:
                validation_result = self._validate_ws_params(params)
                if not validation_result['valid']:
                    # Return error response
                    info_hash = params.get('info_hash', '')
                    action = params['action']
                    response = self.server.ws_parser.create_error_response(
                        action, info_hash, validation_result['error']
                    )
                    return json.dumps(response)

                params.update(validation_result)

            # Handle with core server
            return self.server.handle_websocket_request(socket, message, opts)

        except Exception as e:
            logger.error(f"WebSocket request error: {e}")
            return json.dumps({'failure reason': 'Internal error'})

    def _validate_udp_params(self, params: dict) -> dict:
        """Validate UDP request parameters"""
        try:
            if params['action'] == ACTIONS['ANNOUNCE']:
                # Validate announce parameters
                info_hash = params['info_hash'].lower()
                torrent = Torrent.objects.get(info_hash=info_hash, is_active=True)

                # For private torrents, require authentication
                user = None
                if torrent.is_private:
                    # UDP doesn't support auth tokens, so only allow public torrents
                    return {'valid': False, 'error': 'Authentication required for private torrents'}

                return {'valid': True, 'torrent': torrent, 'user': user}

            elif params['action'] == ACTIONS['SCRAPE']:
                # Scrape validation (basic - just check if torrents exist)
                return {'valid': True}

        except Torrent.DoesNotExist:
            return {'valid': False, 'error': 'Torrent not found'}
        except Exception as e:
            return {'valid': False, 'error': str(e)}

        return {'valid': False, 'error': 'Invalid request'}

    def _validate_ws_params(self, params: dict) -> dict:
        """Validate WebSocket request parameters"""
        try:
            if params['action'] == 'announce':
                # Validate announce parameters
                info_hash = params['info_hash'].lower()
                torrent = Torrent.objects.get(info_hash=info_hash, is_active=True)

                # For private torrents, require authentication
                user = None
                if torrent.is_private:
                    # WebSocket doesn't support auth tokens in URL, so only allow public torrents
                    return {'valid': False, 'error': 'Authentication required for private torrents'}

                return {'valid': True, 'torrent': torrent, 'user': user}

            elif params['action'] == 'scrape':
                # Scrape validation (basic - just check if torrents exist)
                return {'valid': True}

        except Torrent.DoesNotExist:
            return {'valid': False, 'error': 'Torrent not found'}
        except Exception as e:
            return {'valid': False, 'error': str(e)}

        return {'valid': False, 'error': 'Invalid request'}

    def cleanup_expired_data(self):
        """Clean up expired connections and swarms"""
        self.server.cleanup_udp_connections()
        self.server.cleanup_expired_swarms()

    def _error_response(self, message: str) -> HttpResponse:
        """Create error response"""
        response = create_error_response(message)
        return HttpResponse(encode_response(response), content_type='text_plain')

    def get_stats(self) -> dict:
        """Get tracker statistics"""
        return self.server.get_stats()


# Global tracker instance
tracker = DjangoTracker()
