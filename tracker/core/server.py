"""
BitTorrent Tracker Server implementation
"""
import time
import json
import logging
import socket
import threading
from typing import Dict, Optional, Callable, Tuple, Any
from .common import (
    ACTIONS, EVENTS, EVENT_NAMES, DEFAULT_ANNOUNCE_PEERS, MAX_ANNOUNCE_PEERS,
    bin_to_hex, hex_to_bin, parse_querystring, compact_ip_port, IPV4_RE, IPV6_RE
)
from .swarm import Swarm
from .udp_parser import UDPParser
from .websocket_parser import WebSocketParser

logger = logging.getLogger(__name__)


class TrackerServer:
    """
    BitTorrent tracker server that manages multiple torrent swarms
    Supports HTTP, UDP, and WebSocket protocols
    """

    def __init__(self, interval_ms: int = 600000,  # 10 minutes
                 peers_cache_length: int = 1000,
                 peers_cache_ttl: int = 1200000,  # 20 minutes
                 http: bool = True,
                 udp: bool = True,
                 ws: bool = True):

        self.interval_ms = interval_ms
        self.peers_cache_length = peers_cache_length
        self.peers_cache_ttl = peers_cache_ttl

        # Protocol support flags
        self.http_enabled = http
        self.udp_enabled = udp
        self.ws_enabled = ws

        # info_hash -> Swarm mapping
        self.torrents: Dict[str, Swarm] = {}

        # Protocol parsers
        self.udp_parser = UDPParser() if udp else None
        self.ws_parser = WebSocketParser() if ws else None

        # Filter function for allowing/disallowing torrents
        self._filter: Optional[Callable] = None

        # Server sockets (to be set by Django integration)
        self.udp_socket_ipv4: Optional[socket.socket] = None
        self.udp_socket_ipv6: Optional[socket.socket] = None

        logger.info(f"TrackerServer initialized with interval={interval_ms}ms, "
                   f"max_peers_per_swarm={peers_cache_length}, "
                   f"protocols=http:{http} udp:{udp} ws:{ws}")

    def set_filter(self, filter_func: Callable):
        """
        Set a filter function to allow/disallow torrents

        Args:
            filter_func: Function that takes (info_hash, params) and returns True to allow
        """
        self._filter = filter_func

    def create_swarm(self, info_hash: str) -> Swarm:
        """Create a new swarm for the given info_hash"""
        if info_hash in self.torrents:
            return self.torrents[info_hash]

        swarm = Swarm(
            info_hash=info_hash,
            max_peers=self.peers_cache_length,
            peer_ttl=self.peers_cache_ttl // 1000  # Convert to seconds
        )
        self.torrents[info_hash] = swarm
        logger.debug(f"Created swarm for info_hash: {info_hash}")
        return swarm

    def get_swarm(self, info_hash: str) -> Optional[Swarm]:
        """Get existing swarm for the given info_hash"""
        return self.torrents.get(info_hash)

    def handle_announce(self, params: dict) -> dict:
        """
        Handle an announce request

        Args:
            params: Parsed announce parameters

        Returns:
            Response dictionary
        """
        info_hash = params['info_hash']

        # Check filter if set
        if self._filter and not self._filter(info_hash, params):
            raise ValueError("Torrent not allowed")

        # Get or create swarm
        swarm = self.get_swarm(info_hash)
        if not swarm:
            swarm = self.create_swarm(info_hash)

        # Handle the announce
        response = swarm.announce(params)

        # Add interval to response
        response['interval'] = self.interval_ms // 1000  # Convert to seconds
        response['min interval'] = 300  # 5 minutes minimum

        # Emit event
        event_name = params.get('event', 'update')
        if event_name in EVENT_NAMES:
            self._emit_event(EVENT_NAMES[event_name], params)

        logger.debug(f"Announce handled for {info_hash}: {params.get('event', 'update')} "
                    f"from {params['ip']}:{params['port']}")

        return response

    def handle_scrape(self, params: dict) -> dict:
        """
        Handle a scrape request

        Args:
            params: Parsed scrape parameters

        Returns:
            Response dictionary with files data
        """
        info_hashes = params.get('info_hash', [])

        # If no info_hash specified, return all torrents
        if not info_hashes:
            info_hashes = list(self.torrents.keys())

        files = {}
        for info_hash in info_hashes:
            swarm = self.get_swarm(info_hash)
            if swarm:
                stats = swarm.scrape()
                files[info_hash.upper()] = stats
            else:
                # Torrent not found
                files[info_hash.upper()] = {
                    'complete': 0,
                    'incomplete': 0,
                    'downloaded': 0
                }

        response = {
            'files': files,
            'flags': {'min_request_interval': self.interval_ms // 1000}
        }

        logger.debug(f"Scrape handled for {len(info_hashes)} torrents")

        return response

    def _emit_event(self, event_name: str, params: dict):
        """Emit tracker event (for logging/monitoring)"""
        # This can be extended to emit Django signals or custom events
        logger.info(f"Tracker event: {event_name} from {params.get('ip')}:{params.get('port')}")

    def handle_udp_request(self, data: bytes, remote_addr: Tuple[str, int]) -> Optional[bytes]:
        """
        Handle UDP tracker request

        Args:
            data: Raw UDP packet data
            remote_addr: (host, port) tuple

        Returns:
            Response packet data or None
        """
        if not self.udp_parser:
            return None

        # Parse the request
        params = self.udp_parser.parse_request(data, remote_addr)
        if not params:
            return None

        try:
            action = params['action']
            transaction_id = params['transaction_id']

            if action == ACTIONS['CONNECT']:
                # Create new connection
                connection_id = int(time.time() * 1000)  # Use milliseconds for uniqueness
                self.udp_parser.set_connection_id(remote_addr, connection_id)
                return self.udp_parser.create_connect_response(transaction_id)

            elif action == ACTIONS['ANNOUNCE']:
                # Verify connection ID
                if params['connection_id'] != self.udp_parser.get_connection_id(remote_addr):
                    return self.udp_parser.create_error_response(transaction_id, "Invalid connection ID")

                # Handle announce
                response_data = self.handle_announce(params)
                if isinstance(response_data, dict):
                    # Create compact peer list
                    peers_compact = self._create_compact_peers(response_data['peers'])
                    return self.udp_parser.create_announce_response(
                        transaction_id,
                        response_data['interval'],
                        response_data['incomplete'],  # leechers
                        response_data['complete'],    # seeders
                        peers_compact
                    )
                else:
                    # Error response
                    return self.udp_parser.create_error_response(transaction_id, "Announce failed")

            elif action == ACTIONS['SCRAPE']:
                # Verify connection ID
                if params['connection_id'] != self.udp_parser.get_connection_id(remote_addr):
                    return self.udp_parser.create_error_response(transaction_id, "Invalid connection ID")

                # Handle scrape
                response_data = self.handle_scrape(params)
                if isinstance(response_data, dict):
                    stats_list = []
                    for info_hash, stats in response_data['files'].items():
                        stats_list.append({
                            'complete': stats.get('complete', 0),
                            'downloaded': stats.get('downloaded', 0),
                            'incomplete': stats.get('incomplete', 0)
                        })
                    return self.udp_parser.create_scrape_response(transaction_id, stats_list)
                else:
                    return self.udp_parser.create_error_response(transaction_id, "Scrape failed")

        except Exception as e:
            logger.error(f"UDP request error: {e}")
            return self.udp_parser.create_error_response(params.get('transaction_id', 0), "Internal error")

        return None

    def handle_websocket_request(self, socket: Any, message: str, opts: Dict = None) -> Optional[str]:
        """
        Handle WebSocket tracker request

        Args:
            socket: WebSocket connection object
            message: JSON message string
            opts: Parser options

        Returns:
            JSON response string or None
        """
        if not self.ws_parser:
            return None

        if not opts:
            opts = {}

        # Parse the request
        params = self.ws_parser.parse_request(socket, message, opts)
        if not params:
            return None

        try:
            action = params['action']

            if action == 'announce':
                response_data = self.handle_announce(params)
                if isinstance(response_data, dict):
                    response = self.ws_parser.create_announce_response(
                        'announce',
                        params['info_hash'],
                        response_data['interval'],
                        response_data['complete'],
                        response_data['incomplete'],
                        response_data['peers'],
                        params.get('offer_id'),
                        params.get('peer_id'),
                        params.get('offer'),
                        params.get('answer')
                    )
                    return json.dumps(response)
                else:
                    response = self.ws_parser.create_error_response(
                        'announce', params['info_hash'], "Announce failed"
                    )
                    return json.dumps(response)

            elif action == 'scrape':
                response_data = self.handle_scrape(params)
                if isinstance(response_data, dict):
                    response = self.ws_parser.create_scrape_response('scrape', response_data['files'])
                    return json.dumps(response)
                else:
                    # WebSocket scrape doesn't have a specific error format, use announce format
                    response = {'action': 'scrape', 'failure reason': 'Scrape failed'}
                    return json.dumps(response)

        except Exception as e:
            logger.error(f"WebSocket request error: {e}")
            return json.dumps({'failure reason': 'Internal error'})

        return None

    def _create_compact_peers(self, peers: list) -> bytes:
        """Create compact peer list for UDP responses"""
        compact_data = b''
        for peer in peers:
            try:
                peer_bytes = compact_ip_port(peer['ip'], peer['port'])
                compact_data += peer_bytes
            except (ValueError, KeyError):
                continue
        return compact_data

    def cleanup_udp_connections(self):
        """Clean up expired UDP connections"""
        if self.udp_parser:
            self.udp_parser.cleanup_expired_connections()

    def get_stats(self) -> dict:
        """Get server statistics"""
        total_torrents = len(self.torrents)
        active_torrents = sum(1 for swarm in self.torrents.values() if swarm.get_peer_count() > 0)

        total_peers = sum(swarm.get_peer_count() for swarm in self.torrents.values())
        total_seeders = sum(swarm.complete for swarm in self.torrents.values())
        total_leechers = sum(swarm.incomplete for swarm in self.torrents.values())

        return {
            'torrents': total_torrents,
            'active_torrents': active_torrents,
            'peers': total_peers,
            'seeders': total_seeders,
            'leechers': total_leechers,
            'protocols': {
                'http': self.http_enabled,
                'udp': self.udp_enabled,
                'websocket': self.ws_enabled
            }
        }

    def cleanup_expired_swarms(self):
        """Remove empty swarms that have been inactive"""
        empty_swarms = []
        for info_hash, swarm in self.torrents.items():
            if swarm.get_peer_count() == 0:
                empty_swarms.append(info_hash)

        for info_hash in empty_swarms:
            del self.torrents[info_hash]

        if empty_swarms:
            logger.info(f"Cleaned up {len(empty_swarms)} empty swarms")
