"""
HTTP request parsing for BitTorrent tracker
"""
import re
from urllib.parse import urlparse
from .common import (
    ACTIONS, DEFAULT_ANNOUNCE_PEERS, MAX_ANNOUNCE_PEERS,
    bin_to_hex, parse_querystring, IPV6_RE, REMOVE_IPV4_MAPPED_IPV6_RE
)


def parse_http_request(url: str, headers: dict = None, remote_addr: str = None,
                      trust_proxy: bool = False) -> dict:
    """
    Parse HTTP tracker request

    Args:
        url: Full request URL
        headers: HTTP headers dictionary
        remote_addr: Remote IP address
        trust_proxy: Whether to trust X-Forwarded-For header

    Returns:
        Parsed parameters dictionary

    Raises:
        ValueError: If request is invalid
    """
    if not headers:
        headers = {}
    if not remote_addr:
        remote_addr = '127.0.0.1'

    parsed_url = urlparse(url)
    path = parsed_url.path
    query_string = parsed_url.query

    # Parse query parameters
    params = parse_querystring(query_string)

    # Determine action based on path
    if path == '/announce':
        params['action'] = ACTIONS['ANNOUNCE']
        _parse_announce_params(params)
    elif path == '/scrape':
        params['action'] = ACTIONS['SCRAPE']
        _parse_scrape_params(params)
    else:
        raise ValueError(f"Invalid path: {path}")

    # Set peer type
    params['type'] = 'http'

    # Determine client IP
    params['ip'] = _get_client_ip(headers, remote_addr, trust_proxy)

    return params


def _parse_announce_params(params: dict):
    """Parse announce-specific parameters"""
    # Validate info_hash
    info_hash = params.get('info_hash')
    if not isinstance(info_hash, str) or len(info_hash) != 20:
        raise ValueError("Invalid info_hash")
    params['info_hash'] = bin_to_hex(info_hash.encode('latin-1'))

    # Validate peer_id
    peer_id = params.get('peer_id')
    if not isinstance(peer_id, str) or len(peer_id) != 20:
        raise ValueError("Invalid peer_id")
    params['peer_id'] = bin_to_hex(peer_id.encode('latin-1'))

    # Validate port
    try:
        port = int(params.get('port', 0))
        if not (1 <= port <= 65535):
            raise ValueError("Invalid port number")
        params['port'] = port
    except (ValueError, TypeError):
        raise ValueError("Invalid port")

    # Parse numeric parameters
    params['uploaded'] = _parse_int_param(params.get('uploaded', 0))
    params['downloaded'] = _parse_int_param(params.get('downloaded', 0))
    params['left'] = _parse_int_param(params.get('left', 0))

    # Parse compact flag
    params['compact'] = int(params.get('compact', 0))

    # Parse numwant
    numwant = _parse_int_param(params.get('numwant', DEFAULT_ANNOUNCE_PEERS))
    params['numwant'] = min(numwant, MAX_ANNOUNCE_PEERS)

    # Parse event (optional)
    event = params.get('event', 'update')
    if event not in ['started', 'stopped', 'completed', 'update', 'paused']:
        raise ValueError(f"Invalid event: {event}")
    params['event'] = event


def _parse_scrape_params(params: dict):
    """Parse scrape-specific parameters"""
    info_hash = params.get('info_hash')

    if info_hash is None:
        # No info_hash means scrape all torrents
        params['info_hash'] = []
    elif isinstance(info_hash, str):
        # Single info_hash
        if len(info_hash) != 20:
            raise ValueError("Invalid info_hash")
        params['info_hash'] = [bin_to_hex(info_hash.encode('latin-1'))]
    elif isinstance(info_hash, list):
        # Multiple info_hashes
        info_hashes = []
        for ih in info_hash:
            if len(ih) != 20:
                raise ValueError("Invalid info_hash")
            info_hashes.append(bin_to_hex(ih.encode('latin-1')))
        params['info_hash'] = info_hashes
    else:
        raise ValueError("Invalid info_hash format")


def _parse_int_param(value) -> int:
    """Parse integer parameter, defaulting to 0"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _get_client_ip(headers: dict, remote_addr: str, trust_proxy: bool) -> str:
    """Determine client IP address"""
    if trust_proxy:
        x_forwarded_for = headers.get('x-forwarded-for')
        if x_forwarded_for:
            # Take first IP in case of multiple proxies
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = remote_addr
    else:
        ip = remote_addr

    # Remove IPv4-mapped IPv6 prefix
    ip = REMOVE_IPV4_MAPPED_IPV6_RE.sub('', ip)

    return ip
