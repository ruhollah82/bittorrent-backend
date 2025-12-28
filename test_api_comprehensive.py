#!/usr/bin/env python3
"""
Comprehensive API Testing Script
Tests all API endpoints and verifies functionality
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

# Configuration
BASE_URL = "http://localhost:8000"
if len(sys.argv) > 1:
    BASE_URL = sys.argv[1]

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_data: Optional[Dict] = None
        self.test_results = []
        self.invite_code: Optional[str] = None
        
    def log(self, message: str, success: bool = True, details: str = ""):
        """Log test results with colors"""
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if success else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"{status}: {message}")
        if details:
            print(f"   {Colors.BLUE}Details: {details}{Colors.RESET}")
        self.test_results.append({
            "message": message,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{title:^60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    def test_health_check(self) -> bool:
        """Test health check endpoint"""
        self.print_header("Health Check")
        try:
            response = self.session.get(f"{self.base_url}/api/logs/health/")
            if response.status_code == 200:
                data = response.json()
                self.log("Health check endpoint", True, f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.log("Health check endpoint", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log("Health check endpoint", False, str(e))
            return False
    
    def test_api_docs(self) -> bool:
        """Test API documentation endpoints"""
        self.print_header("API Documentation")
        endpoints = [
            ("/api/schema/", "OpenAPI Schema"),
            ("/api/docs/", "Swagger UI"),
            ("/api/redoc/", "ReDoc"),
        ]
        all_passed = True
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    self.log(f"{name} accessible", True)
                else:
                    self.log(f"{name} accessible", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log(f"{name} accessible", False, str(e))
                all_passed = False
        return all_passed
    
    def test_authentication(self) -> bool:
        """Test authentication endpoints"""
        self.print_header("Authentication Tests")
        
        # Test registration (will fail if user exists, that's OK)
        register_data = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "invite_code": ""  # Will need to get/create one
        }
        
        try:
            response = self.session.post(f"{self.base_url}/api/auth/register/", json=register_data)
            if response.status_code in [201, 400]:  # 400 if invite code needed or user exists
                if response.status_code == 201:
                    data = response.json()
                    self.log("User registration", True, f"User: {register_data['username']}")
                else:
                    error = response.json()
                    if "invite_code" in str(error):
                        self.log("User registration", True, "Requires invite code (expected)")
                    else:
                        self.log("User registration", False, f"Error: {error}")
            else:
                self.log("User registration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log("User registration", False, str(e))
        
        # Test login (using admin or existing test user)
        login_data = {
            "username": "admin",  # Default admin
            "password": "admin123"  # Common default
        }
        
        try:
            response = self.session.post(f"{self.base_url}/api/auth/login/", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access")
                self.refresh_token = data.get("refresh")
                self.user_data = data.get("user")
                if self.access_token:
                    self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                    self.log("User login", True, f"User: {data.get('user', {}).get('username', 'unknown')}")
                    return True
                else:
                    self.log("User login", False, "No access token in response")
                    return False
            else:
                self.log("User login", False, f"Status: {response.status_code}, Try creating admin user first")
                return False
        except Exception as e:
            self.log("User login", False, str(e))
            return False
    
    def test_user_endpoints(self) -> bool:
        """Test user management endpoints"""
        if not self.access_token:
            self.log("User endpoints", False, "Not authenticated")
            return False
        
        self.print_header("User Management Tests")
        all_passed = True
        
        endpoints = [
            ("/api/user/profile/", "GET", "User profile"),
            ("/api/user/stats/", "GET", "User statistics"),
            ("/api/user/tokens/", "GET", "Auth tokens list"),
        ]
        
        for endpoint, method, name in endpoints:
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}")
                else:
                    response = self.session.post(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"{name}", True, f"Data received: {len(str(data))} chars")
                else:
                    self.log(f"{name}", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log(f"{name}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_torrent_endpoints(self) -> bool:
        """Test torrent management endpoints"""
        if not self.access_token:
            self.log("Torrent endpoints", False, "Not authenticated")
            return False
        
        self.print_header("Torrent Management Tests")
        all_passed = True
        
        # Test torrent list
        try:
            response = self.session.get(f"{self.base_url}/api/torrents/")
            if response.status_code == 200:
                data = response.json()
                count = data.get("count", len(data.get("results", [])))
                self.log("Torrent list", True, f"Found {count} torrents")
            else:
                self.log("Torrent list", False, f"Status: {response.status_code}")
                all_passed = False
        except Exception as e:
            self.log("Torrent list", False, str(e))
            all_passed = False
        
        # Test categories
        try:
            response = self.session.get(f"{self.base_url}/api/torrents/categories/")
            if response.status_code == 200:
                data = response.json()
                self.log("Torrent categories", True, f"Found {len(data)} categories")
            else:
                self.log("Torrent categories", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log("Torrent categories", False, str(e))
        
        # Test popular torrents
        try:
            response = self.session.get(f"{self.base_url}/api/torrents/popular/")
            if response.status_code == 200:
                data = response.json()
                self.log("Popular torrents", True, f"Found {len(data.get('results', []))} torrents")
            else:
                self.log("Popular torrents", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log("Popular torrents", False, str(e))
        
        return all_passed
    
    def test_credits_endpoints(self) -> bool:
        """Test credit system endpoints"""
        if not self.access_token:
            self.log("Credit endpoints", False, "Not authenticated")
            return False
        
        self.print_header("Credit System Tests")
        all_passed = True
        
        endpoints = [
            ("/api/credits/balance/", "GET", "Credit balance"),
            ("/api/credits/transactions/", "GET", "Transaction history"),
            ("/api/credits/ratio-status/", "GET", "Ratio status"),
        ]
        
        for endpoint, method, name in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"{name}", True, f"Data: {json.dumps(data)[:100]}")
                else:
                    self.log(f"{name}", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log(f"{name}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_security_endpoints(self) -> bool:
        """Test security monitoring endpoints"""
        if not self.access_token:
            self.log("Security endpoints", False, "Not authenticated")
            return False
        
        self.print_header("Security & Monitoring Tests")
        all_passed = True
        
        try:
            response = self.session.get(f"{self.base_url}/api/security/stats/")
            if response.status_code == 200:
                data = response.json()
                self.log("Security statistics", True, f"Stats received")
            else:
                self.log("Security statistics", False, f"Status: {response.status_code}")
                all_passed = False
        except Exception as e:
            self.log("Security statistics", False, str(e))
            all_passed = False
        
        return all_passed
    
    def test_admin_endpoints(self) -> bool:
        """Test admin panel endpoints (may require admin privileges)"""
        if not self.access_token:
            self.log("Admin endpoints", False, "Not authenticated")
            return False
        
        self.print_header("Admin Panel Tests")
        
        try:
            response = self.session.get(f"{self.base_url}/api/admin/dashboard/")
            if response.status_code == 200:
                data = response.json()
                self.log("Admin dashboard", True, "Accessible")
            elif response.status_code == 403:
                self.log("Admin dashboard", True, "Requires admin privileges (expected)")
            else:
                self.log("Admin dashboard", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log("Admin dashboard", False, str(e))
        
        return True
    
    def run_all_tests(self):
        """Run all API tests"""
        print(f"\n{Colors.BOLD}{Colors.YELLOW}Starting Comprehensive API Tests{Colors.RESET}")
        print(f"{Colors.BLUE}Base URL: {self.base_url}{Colors.RESET}\n")
        
        # Run tests
        self.test_health_check()
        self.test_api_docs()
        auth_success = self.test_authentication()
        
        if auth_success:
            self.test_user_endpoints()
            self.test_torrent_endpoints()
            self.test_credits_endpoints()
            self.test_security_endpoints()
            self.test_admin_endpoints()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Summary")
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        
        print(f"{Colors.BOLD}Total Tests: {total}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"{Colors.BLUE}Success Rate: {(passed/total*100):.1f}%{Colors.RESET}\n")
        
        if failed > 0:
            print(f"{Colors.RED}Failed Tests:{Colors.RESET}")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['message']}: {result['details']}")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()

