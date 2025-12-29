"""
Bencode encoding/decoding utilities for BitTorrent tracker responses
"""
import bencode
from .common import IPV4_RE, compact_ip_port


def encode_response(data: dict) -> bytes:
    """
    Encode response data as bencoded bytes

    Args:
        data: Response dictionary

    Returns:
        Bencoded bytes
    """
    return bencode.encode(data)


def create_peer_list(peers: list, compact: bool = False) -> bytes:
    """
    Create peer list in the appropriate format

    Args:
        peers: List of peer dictionaries with 'ip', 'port', 'peer_id' keys
        compact: Whether to use compact format

    Returns:
        Peer list in the requested format
    """
    if compact:
        return _create_compact_peer_list(peers)
    else:
        return _create_dict_peer_list(peers)


def _create_compact_peer_list(peers: list) -> bytes:
    """Create compact peer list (binary format)"""
    compact_data = b''

    for peer in peers:
        try:
            peer_bytes = compact_ip_port(peer['ip'], peer['port'])
            compact_data += peer_bytes
        except (ValueError, KeyError):
            # Skip invalid peers
            continue

    return compact_data


def _create_dict_peer_list(peers: list) -> list:
    """Create dictionary peer list"""
    peer_list = []

    for peer in peers:
        try:
            peer_dict = {
                'ip': peer['ip'],
                'port': peer['port'],
                'peer id': peer.get('peer_id', '')
            }
            peer_list.append(peer_dict)
        except KeyError:
            # Skip invalid peers
            continue

    return peer_list


def create_announce_response(complete: int, incomplete: int, peers: list,
                           interval: int, compact: bool = False) -> dict:
    """
    Create announce response dictionary

    Args:
        complete: Number of seeders
        incomplete: Number of leechers
        peers: List of peer dictionaries
        interval: Announce interval in seconds
        compact: Whether to use compact peer format

    Returns:
        Response dictionary ready for bencoding
    """
    response = {
        'interval': interval,
        'complete': complete,
        'incomplete': incomplete,
        'peers': create_peer_list(peers, compact)
    }

    return response


def create_scrape_response(files: dict) -> dict:
    """
    Create scrape response dictionary

    Args:
        files: Dictionary mapping info_hash to stats

    Returns:
        Response dictionary ready for bencoding
    """
    response = {'files': files}
    return response


def create_error_response(message: str) -> dict:
    """
    Create error response dictionary

    Args:
        message: Error message

    Returns:
        Response dictionary ready for bencoding
    """
    return {'failure reason': message}
