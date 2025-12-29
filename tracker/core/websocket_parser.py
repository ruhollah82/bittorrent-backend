"""
WebSocket BitTorrent tracker protocol parser
Based on WebTorrent tracker specification
"""
import json
import time
from typing import Dict, Optional, Any
from .common import bin_to_hex, hex_to_bin, DEFAULT_ANNOUNCE_PEERS, MAX_ANNOUNCE_PEERS


class WebSocketParser:
    """WebSocket tracker request/response parser"""

    def parse_request(self, socket, message: str, opts: Dict = None) -> Optional[Dict]:
        """
        Parse WebSocket tracker request

        Args:
            socket: WebSocket connection object
            message: JSON message string
            opts: Parser options

        Returns:
            Parsed request parameters or None if invalid
        """
        if not opts:
            opts = {}

        try:
            data = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return None

        # Basic validation
        if not isinstance(data, dict) or 'action' not in data:
            return None

        action = data.get('action')
        if action not in ['announce', 'scrape']:
            return None

        params = {
            'action': action,
            'type': 'ws',
            'socket': socket,
            'peer_id': getattr(socket, 'peer_id', None)
        }

        # Parse action-specific data
        if action == 'announce':
            return self._parse_announce_request(params, data, opts)
        elif action == 'scrape':
            return self._parse_scrape_request(params, data, opts)

        return None

    def _parse_announce_request(self, params: Dict, data: Dict, opts: Dict) -> Optional[Dict]:
        """Parse WebSocket announce request"""
        try:
            # Required parameters
            info_hash = data.get('info_hash')
            if not info_hash:
                return None

            # Convert from binary to hex if needed
            if isinstance(info_hash, (bytes, bytearray)):
                info_hash = bin_to_hex(bytes(info_hash))
            params['info_hash'] = info_hash.lower()

            # Optional parameters with defaults
            params.update({
                'peer_id': data.get('peer_id', params.get('peer_id')),
                'uploaded': data.get('uploaded', 0),
                'downloaded': data.get('downloaded', 0),
                'left': data.get('left', 0),
                'event': data.get('event', 'update'),
                'numwant': min(data.get('numwant', DEFAULT_ANNOUNCE_PEERS), MAX_ANNOUNCE_PEERS),
                'offers': data.get('offers', []),
                'answer': data.get('answer'),
                'offer_id': data.get('offer_id'),
                'to_peer_id': data.get('to_peer_id')
            })

            # Determine IP address
            params['ip'] = self._get_client_ip(opts.get('trustProxy', False),
                                             getattr(opts, 'remote_addr', None),
                                             getattr(opts, 'headers', {}))

            # Generate address
            port = getattr(socket, 'remote_port', 0) if 'socket' in locals() else 0
            params['port'] = port
            params['addr'] = f"{params['ip']}:{port}"

            return params

        except (KeyError, ValueError, TypeError):
            return None

    def _parse_scrape_request(self, params: Dict, data: Dict, opts: Dict) -> Optional[Dict]:
        """Parse WebSocket scrape request"""
        try:
            info_hash = data.get('info_hash')

            if info_hash is None:
                # Scrape all torrents
                params['info_hash'] = []
            elif isinstance(info_hash, str):
                # Single info_hash
                params['info_hash'] = [info_hash.lower()]
            elif isinstance(info_hash, list):
                # Multiple info_hashes
                params['info_hash'] = [ih.lower() for ih in info_hash]
            else:
                return None

            return params

        except (TypeError, AttributeError):
            return None

    def _get_client_ip(self, trust_proxy: bool, remote_addr: str = None, headers: Dict = None) -> str:
        """Get client IP address from WebSocket connection"""
        if not headers:
            headers = {}

        if trust_proxy:
            x_forwarded_for = headers.get('x-forwarded-for')
            if x_forwarded_for:
                # Take first IP in case of multiple proxies
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = remote_addr or '127.0.0.1'
        else:
            ip = remote_addr or '127.0.0.1'

        return ip

    def create_announce_response(self, action: str, info_hash: str, interval: int,
                               complete: int, incomplete: int, peers: list,
                               offer_id: str = None, peer_id: str = None,
                               offer: Dict = None, answer: Dict = None) -> Dict:
        """Create WebSocket announce response"""
        response = {
            'action': action,
            'info_hash': info_hash,  # Keep as hex string for JSON compatibility
            'interval': interval,
            'complete': complete,
            'incomplete': incomplete,
            'peers': peers
        }

        # Add WebRTC-specific fields if present
        if offer_id:
            response['offer_id'] = offer_id
        if peer_id:
            response['peer_id'] = peer_id  # Keep as hex string for JSON
        if offer:
            response['offer'] = offer
        if answer:
            response['answer'] = answer

        return response

    def create_scrape_response(self, action: str, files: Dict) -> Dict:
        """Create WebSocket scrape response"""
        response = {
            'action': action,
            'files': {}
        }

        # Keep info_hashes as hex strings for JSON compatibility
        for info_hash, stats in files.items():
            response['files'][info_hash] = stats

        return response

    def create_error_response(self, action: str, info_hash: str, message: str) -> Dict:
        """Create WebSocket error response"""
        return {
            'action': action,
            'info_hash': info_hash,  # Keep as hex string for JSON
            'failure reason': message
        }
