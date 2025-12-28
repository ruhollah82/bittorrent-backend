#!/usr/bin/env python3
"""
BitTorrent Tracker Simulator
Simulates seeder and leecher clients to test tracker functionality
"""

import requests
import bencode
import time
import random
import string
import sys
import threading
from typing import Dict, Optional, List
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
if len(sys.argv) > 1:
    BASE_URL = sys.argv[1]

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class BitTorrentClient:
    """Simulates a BitTorrent client"""
    
    def __init__(self, client_name: str, base_url: str = BASE_URL):
        self.client_name = client_name
        self.base_url = base_url
        self.peer_id = self.generate_peer_id(client_name)
        self.port = random.randint(6881, 6999)
        self.info_hash: Optional[str] = None
        self.auth_token: Optional[str] = None
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.is_seeder = False
        self.is_active = False
        self.session = requests.Session()
        
    @staticmethod
    def generate_peer_id(client_name: str) -> str:
        """Generate a valid peer ID"""
        # BitTorrent peer IDs are 20 bytes
        # Format: -[client]-[random]
        prefix = f"-{client_name[:2]}-"
        random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=20 - len(prefix)))
        return (prefix + random_part)[:20]
    
    def set_torrent(self, info_hash: str, torrent_size: int, auth_token: Optional[str] = None):
        """Set torrent information"""
        self.info_hash = info_hash.lower()
        self.left = torrent_size
        self.auth_token = auth_token
        self.is_seeder = False
    
    def set_auth_token(self, auth_token: str):
        """Set authentication token"""
        self.auth_token = auth_token
    
    def announce(self, event: str = "started") -> Dict:
        """Send announce request to tracker"""
        if not self.info_hash:
            return {"error": "No torrent set"}
        
        params = {
            "info_hash": self.info_hash,
            "peer_id": self.peer_id,
            "port": str(self.port),
            "uploaded": str(self.uploaded),
            "downloaded": str(self.downloaded),
            "left": str(self.left),
            "compact": "1",
            "event": event,
        }
        
        if self.auth_token:
            params["auth_token"] = self.auth_token
        
        try:
            response = self.session.get(f"{self.base_url}/announce", params=params, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = bencode.decode(response.content)
                    return data
                except Exception as e:
                    return {"error": f"Failed to decode response: {e}"}
            else:
                return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            return {"error": f"Request failed: {e}"}
    
    def scrape(self) -> Dict:
        """Send scrape request to tracker"""
        if not self.info_hash:
            return {"error": "No torrent set"}
        
        params = {}
        if self.info_hash:
            params["info_hash"] = self.info_hash
        if self.auth_token:
            params["auth_token"] = self.auth_token
        
        try:
            response = self.session.get(f"{self.base_url}/scrape", params=params, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = bencode.decode(response.content)
                    return data
                except Exception as e:
                    return {"error": f"Failed to decode response: {e}"}
            else:
                return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            return {"error": f"Request failed: {e}"}
    
    def simulate_download(self, torrent_size: int, speed_bytes_per_sec: int = 1024 * 1024):
        """Simulate downloading a torrent"""
        print(f"{Colors.CYAN}[{self.client_name}] Starting download simulation...{Colors.RESET}")
        
        # Initial announce
        result = self.announce("started")
        if "error" in result:
            print(f"{Colors.RED}[{self.client_name}] Announce failed: {result['error']}{Colors.RESET}")
            return False
        
        print(f"{Colors.GREEN}[{self.client_name}] Connected to tracker{Colors.RESET}")
        print(f"{Colors.BLUE}[{self.client_name}] Interval: {result.get('interval', 'N/A')} seconds{Colors.RESET}")
        print(f"{Colors.BLUE}[{self.client_name}] Peers: {len(result.get('peers', b'')) // 6 if isinstance(result.get('peers'), bytes) else len(result.get('peers', []))}{Colors.RESET}")
        
        # Simulate download progress
        chunk_size = speed_bytes_per_sec // 10  # Update 10 times per second
        downloaded_this_round = 0
        
        while self.left > 0:
            time.sleep(0.1)  # 100ms intervals
            
            # Simulate download
            download_chunk = min(chunk_size, self.left)
            self.downloaded += download_chunk
            self.left -= download_chunk
            downloaded_this_round += download_chunk
            
            # Announce progress every 5 seconds
            if downloaded_this_round >= speed_bytes_per_sec * 5:
                result = self.announce()
                if "error" in result:
                    print(f"{Colors.RED}[{self.client_name}] Announce error: {result['error']}{Colors.RESET}")
                else:
                    progress = ((torrent_size - self.left) / torrent_size) * 100
                    print(f"{Colors.YELLOW}[{self.client_name}] Progress: {progress:.1f}% ({self.downloaded / (1024*1024):.2f} MB downloaded){Colors.RESET}")
                downloaded_this_round = 0
        
        # Complete download
        self.left = 0
        self.is_seeder = True
        result = self.announce("completed")
        
        if "error" in result:
            print(f"{Colors.RED}[{self.client_name}] Completion announce failed: {result['error']}{Colors.RESET}")
            return False
        
        print(f"{Colors.GREEN}[{self.client_name}] Download completed! Now seeding...{Colors.RESET}")
        return True
    
    def simulate_seeding(self, duration_seconds: int = 60, announce_interval: int = 30):
        """Simulate seeding a torrent"""
        print(f"{Colors.CYAN}[{self.client_name}] Starting seeding simulation...{Colors.RESET}")
        
        self.is_seeder = True
        self.left = 0
        start_time = time.time()
        last_announce = 0
        
        # Initial announce
        result = self.announce("started")
        if "error" in result:
            print(f"{Colors.RED}[{self.client_name}] Announce failed: {result['error']}{Colors.RESET}")
            return False
        
        print(f"{Colors.GREEN}[{self.client_name}] Seeding started{Colors.RESET}")
        
        while time.time() - start_time < duration_seconds:
            time.sleep(1)
            
            # Simulate upload
            upload_chunk = random.randint(1024, 1024 * 100)  # 1KB to 100KB per second
            self.uploaded += upload_chunk
            
            # Announce at intervals
            if time.time() - last_announce >= announce_interval:
                result = self.announce()
                if "error" in result:
                    print(f"{Colors.RED}[{self.client_name}] Announce error: {result['error']}{Colors.RESET}")
                else:
                    peers = len(result.get('peers', b'')) // 6 if isinstance(result.get('peers'), bytes) else len(result.get('peers', []))
                    print(f"{Colors.GREEN}[{self.client_name}] Seeding - Uploaded: {self.uploaded / (1024*1024):.2f} MB, Peers: {peers}{Colors.RESET}")
                last_announce = time.time()
        
        # Stop seeding
        result = self.announce("stopped")
        print(f"{Colors.YELLOW}[{self.client_name}] Seeding stopped{Colors.RESET}")
        return True


class TrackerSimulator:
    """Simulates multiple BitTorrent clients"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.clients: List[BitTorrentClient] = []
        self.test_results = []
    
    def create_client(self, client_name: str) -> BitTorrentClient:
        """Create a new BitTorrent client"""
        client = BitTorrentClient(client_name, self.base_url)
        self.clients.append(client)
        return client
    
    def test_basic_announce(self, info_hash: str, auth_token: Optional[str] = None) -> bool:
        """Test basic announce functionality"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}Testing Basic Announce{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        client = self.create_client("TEST")
        client.set_torrent(info_hash, 100 * 1024 * 1024, auth_token)  # 100MB
        
        result = client.announce("started")
        
        if "error" in result:
            print(f"{Colors.RED}❌ Announce failed: {result['error']}{Colors.RESET}")
            return False
        
        if "failure reason" in result:
            print(f"{Colors.RED}❌ Tracker error: {result['failure reason']}{Colors.RESET}")
            return False
        
        print(f"{Colors.GREEN}✅ Announce successful!{Colors.RESET}")
        print(f"   Interval: {result.get('interval', 'N/A')} seconds")
        print(f"   Min interval: {result.get('min interval', 'N/A')} seconds")
        
        peers = result.get('peers', b'')
        if isinstance(peers, bytes):
            peer_count = len(peers) // 6
        else:
            peer_count = len(peers)
        print(f"   Peers: {peer_count}")
        
        return True
    
    def test_scrape(self, info_hash: str, auth_token: Optional[str] = None) -> bool:
        """Test scrape functionality"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}Testing Scrape{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        client = self.create_client("SCRAPE")
        client.set_torrent(info_hash, 0, auth_token)
        if auth_token:
            client.set_auth_token(auth_token)
        
        result = client.scrape()
        
        if "error" in result:
            print(f"{Colors.RED}❌ Scrape failed: {result['error']}{Colors.RESET}")
            return False
        
        if "failure reason" in result:
            print(f"{Colors.RED}❌ Tracker error: {result['failure reason']}{Colors.RESET}")
            return False
        
        print(f"{Colors.GREEN}✅ Scrape successful!{Colors.RESET}")
        
        files = result.get('files', {})
        for hash_val, stats in files.items():
            print(f"   Torrent: {hash_val[:20]}...")
            print(f"     Complete (seeders): {stats.get('complete', 0)}")
            print(f"     Downloaded: {stats.get('downloaded', 0)}")
            print(f"     Incomplete (leechers): {stats.get('incomplete', 0)}")
        
        return True
    
    def simulate_seeder_leecher(self, info_hash: str, torrent_size: int, 
                                auth_token: Optional[str] = None, 
                                num_leechers: int = 2) -> bool:
        """Simulate one seeder and multiple leechers"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}Simulating Seeder and {num_leechers} Leechers{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        # Create seeder
        seeder = self.create_client("SEEDER")
        seeder.set_torrent(info_hash, torrent_size, auth_token)
        seeder.is_seeder = True
        seeder.left = 0
        seeder.downloaded = torrent_size
        
        print(f"{Colors.GREEN}🌱 Seeder created: {seeder.peer_id}{Colors.RESET}")
        
        # Create leechers
        leechers = []
        for i in range(num_leechers):
            leecher = self.create_client(f"LEECH{i+1}")
            leecher.set_torrent(info_hash, torrent_size, auth_token)
            leechers.append(leecher)
            print(f"{Colors.YELLOW}📥 Leecher {i+1} created: {leecher.peer_id}{Colors.RESET}")
        
        # Start seeder
        seeder_result = seeder.announce("started")
        if "error" in seeder_result or "failure reason" in seeder_result:
            print(f"{Colors.RED}❌ Seeder announce failed{Colors.RESET}")
            return False
        print(f"{Colors.GREEN}✅ Seeder connected to tracker{Colors.RESET}")
        
        # Start leechers
        for i, leecher in enumerate(leechers):
            leecher_result = leecher.announce("started")
            if "error" in leecher_result or "failure reason" in leecher_result:
                print(f"{Colors.RED}❌ Leecher {i+1} announce failed{Colors.RESET}")
            else:
                peers = leecher_result.get('peers', b'')
                peer_count = len(peers) // 6 if isinstance(peers, bytes) else len(peers)
                print(f"{Colors.GREEN}✅ Leecher {i+1} connected - Found {peer_count} peers{Colors.RESET}")
        
        # Simulate activity
        print(f"\n{Colors.CYAN}Simulating activity for 30 seconds...{Colors.RESET}")
        
        def seeder_thread():
            seeder.simulate_seeding(30, 10)
        
        def leecher_thread(leecher, index):
            # Simulate partial download
            download_amount = torrent_size // (num_leechers + 1) * (index + 1)
            leecher.downloaded = download_amount
            leecher.left = torrent_size - download_amount
            
            # Periodic announces
            for _ in range(3):
                time.sleep(10)
                result = leecher.announce()
                if "error" not in result and "failure reason" not in result:
                    progress = ((torrent_size - leecher.left) / torrent_size) * 100
                    print(f"{Colors.YELLOW}[LEECH{index+1}] Progress: {progress:.1f}%{Colors.RESET}")
        
        # Start threads
        threads = []
        threads.append(threading.Thread(target=seeder_thread))
        for i, leecher in enumerate(leechers):
            threads.append(threading.Thread(target=leecher_thread, args=(leecher, i)))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        print(f"\n{Colors.GREEN}✅ Simulation completed!{Colors.RESET}")
        return True
    
    def run_comprehensive_test(self, info_hash: str, auth_token: Optional[str] = None):
        """Run comprehensive tracker tests"""
        print(f"\n{Colors.BOLD}{Colors.YELLOW}BitTorrent Tracker Simulator{Colors.RESET}")
        print(f"{Colors.BLUE}Base URL: {self.base_url}{Colors.RESET}")
        print(f"{Colors.BLUE}Info Hash: {info_hash}{Colors.RESET}\n")
        
        # Test basic announce
        self.test_basic_announce(info_hash, auth_token)
        
        # Test scrape
        self.test_scrape(info_hash, auth_token)
        
        # Simulate seeder/leecher
        self.simulate_seeder_leecher(info_hash, 100 * 1024 * 1024, auth_token, num_leechers=2)


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print(f"{Colors.RED}Usage: {sys.argv[0]} <info_hash> [auth_token] [base_url]{Colors.RESET}")
        print(f"{Colors.YELLOW}Example: {sys.argv[0]} aabbccddeeff00112233445566778899aabbccdd{Colors.RESET}")
        print(f"{Colors.YELLOW}Example: {sys.argv[0]} aabbccddeeff00112233445566778899aabbccdd my_token http://localhost:8000{Colors.RESET}")
        sys.exit(1)
    
    info_hash = sys.argv[1]
    auth_token = sys.argv[2] if len(sys.argv) > 2 else None
    base_url = sys.argv[3] if len(sys.argv) > 3 else BASE_URL
    
    simulator = TrackerSimulator(base_url)
    simulator.run_comprehensive_test(info_hash, auth_token)


if __name__ == "__main__":
    main()

