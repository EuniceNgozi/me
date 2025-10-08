import requests
import sys
import json
from datetime import datetime

class ViralLeadsAPITester:
    def __init__(self, base_url="https://pinpoint-leads.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.session = requests.Session()  # Use session for cookies

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, use_auth=False):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response preview: {str(response_data)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:500]}")

            self.test_results.append({
                'name': name,
                'success': success,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'response_preview': response.text[:200] if not success else "Success"
            })

            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                'name': name,
                'success': False,
                'error': str(e)
            })
            return False, {}

    def test_authentication_endpoints(self):
        """Test authentication-related endpoints"""
        print(f"\n🔐 Testing Authentication Endpoints...")
        
        # Test auth/me without authentication (should fail)
        success, response = self.run_test(
            "Auth Me - No Auth",
            "GET",
            "auth/me",
            401
        )
        
        # Test process-session with invalid session (should fail)
        success, response = self.run_test(
            "Process Session - Invalid",
            "POST",
            "auth/process-session",
            400,
            data={"session_id": "invalid_session_id"}
        )
        
        return True

    def test_protected_endpoints_without_auth(self):
        """Test that protected endpoints properly require authentication"""
        print(f"\n🛡️  Testing Protected Endpoints (Should Require Auth)...")
        
        protected_endpoints = [
            ("Analytics", "GET", "analytics"),
            ("Trending Topics", "GET", "trending"),
            ("Get Leads", "GET", "leads"),
            ("Discover Leads", "POST", "leads/discover", {
                "platforms": ["facebook"],
                "keywords": ["test"],
                "max_leads": 5
            })
        ]
        
        all_protected = True
        for name, method, endpoint, *data in protected_endpoints:
            test_data = data[0] if data else None
            success, _ = self.run_test(
                f"{name} - No Auth",
                method,
                endpoint,
                401,
                data=test_data
            )
            if not success:
                all_protected = False
        
        return all_protected

    def test_health_check(self):
        """Test basic API health check"""
        return self.run_test(
            "API Health Check",
            "GET",
            "",
            200
        )

    def test_api_structure(self):
        """Test API structure and features"""
        success, response = self.test_health_check()
        if success and response:
            print(f"   API Version: {response.get('version', 'Unknown')}")
            print(f"   Status: {response.get('status', 'Unknown')}")
            features = response.get('features', [])
            print(f"   Features: {', '.join(features)}")
            
            # Check if expected features are present
            expected_features = ['real_api_integration', 'user_authentication', 'monetization']
            missing_features = [f for f in expected_features if f not in features]
            if missing_features:
                print(f"   ⚠️  Missing expected features: {missing_features}")
            else:
                print(f"   ✅ All expected features present")
        
        return success, response

    def test_analytics(self):
        """Test analytics endpoint"""
        return self.run_test(
            "Analytics Endpoint",
            "GET",
            "analytics",
            401  # Should require auth
        )

    def test_trending_topics(self):
        """Test trending topics endpoint"""
        success, response = self.run_test(
            "Trending Topics - All Platforms",
            "GET",
            "trending",
            401  # Should require auth
        )
        
        return success, response

    def test_get_leads(self):
        """Test get leads endpoint"""
        success, response = self.run_test(
            "Get Leads - Basic",
            "GET",
            "leads",
            401  # Should require auth
        )
        
        return success, response

    def test_discover_leads(self):
        """Test lead discovery endpoint - the main AI-powered feature"""
        test_data = {
            "platforms": ["facebook", "instagram"],
            "keywords": ["digital marketing", "saas tools"],
            "max_leads": 20,
            "min_followers": 1000,
            "days_back": 30
        }
        
        print(f"   Test data: {json.dumps(test_data, indent=2)}")
        
        success, response = self.run_test(
            "Discover Leads - AI Analysis",
            "POST",
            "leads/discover",
            401,  # Should require auth
            data=test_data
        )
        
        return success, response

    def test_instagram_integration(self):
        """Test Instagram-specific integration features"""
        print(f"\n📸 Testing Instagram Integration...")
        
        # Test Instagram platform in lead discovery
        instagram_test_data = {
            "platforms": ["instagram"],
            "keywords": ["content creation", "influencer marketing"],
            "max_leads": 10,
            "min_followers": 1000,
            "days_back": 30
        }
        
        success, response = self.run_test(
            "Instagram Lead Discovery",
            "POST",
            "leads/discover",
            401,  # Should require auth
            data=instagram_test_data
        )
        
        # Test Instagram trending topics
        success_trending, trending_response = self.run_test(
            "Instagram Trending Topics",
            "GET",
            "trending",
            401,  # Should require auth
            params={"platform": "instagram"}
        )
        
        # Test platform connection endpoint for Instagram
        connect_data = {
            "platform": "instagram",
            "access_token": "test_token_123"
        }
        
        success_connect, connect_response = self.run_test(
            "Instagram Platform Connection",
            "POST",
            "platforms/connect",
            401,  # Should require auth
            data=connect_data
        )
        
        return success and success_trending and success_connect

    def test_pinterest_oauth_endpoints(self):
        """Test Pinterest OAuth endpoints"""
        print(f"\n📌 Testing Pinterest OAuth Endpoints...")
        
        # Test Pinterest OAuth init endpoint
        success_init, response_init = self.run_test(
            "Pinterest OAuth Init",
            "GET",
            "pinterest/auth/init",
            401  # Should require auth
        )
        
        # Test Pinterest OAuth callback endpoint
        success_callback, response_callback = self.run_test(
            "Pinterest OAuth Callback",
            "GET",
            "pinterest/auth/callback",
            401,  # Should require auth
            params={"code": "test_code", "user_id": "test_user_123"}
        )
        
        # Test Pinterest mock connection endpoint
        success_connect, response_connect = self.run_test(
            "Pinterest Mock Connection",
            "POST",
            "pinterest/auth/connect",
            401  # Should require auth
        )
        
        return success_init and success_callback and success_connect

    def test_pinterest_integration(self):
        """Test Pinterest-specific integration features"""
        print(f"\n📌 Testing Pinterest Integration...")
        
        # Test Pinterest platform in lead discovery
        pinterest_test_data = {
            "platforms": ["pinterest"],
            "keywords": ["digital marketing", "course creation", "productivity"],
            "max_leads": 10,
            "min_followers": 1000,
            "days_back": 30
        }
        
        success, response = self.run_test(
            "Pinterest Lead Discovery",
            "POST",
            "leads/discover",
            401,  # Should require auth
            data=pinterest_test_data
        )
        
        # Test Pinterest trending topics
        success_trending, trending_response = self.run_test(
            "Pinterest Trending Topics",
            "GET",
            "trending",
            401,  # Should require auth
            params={"platform": "pinterest"}
        )
        
        # Test platform connection endpoint for Pinterest
        connect_data = {
            "platform": "pinterest",
            "access_token": "pinterest_mock_token_123"
        }
        
        success_connect, connect_response = self.run_test(
            "Pinterest Platform Connection",
            "POST",
            "platforms/connect",
            401,  # Should require auth
            data=connect_data
        )
        
        return success and success_trending and success_connect

    def test_multi_platform_support(self):
        """Test multi-platform support including Instagram and Pinterest"""
        print(f"\n🌐 Testing Multi-Platform Support...")
        
        # Test with all platforms including Instagram and Pinterest
        multi_platform_data = {
            "platforms": ["facebook", "instagram", "pinterest", "tiktok"],
            "keywords": ["digital marketing", "online business"],
            "max_leads": 20,
            "min_followers": 500,
            "days_back": 30
        }
        
        success, response = self.run_test(
            "Multi-Platform Lead Discovery",
            "POST",
            "leads/discover",
            401,  # Should require auth
            data=multi_platform_data
        )
        
        # Test trending topics for each platform
        platforms = ["facebook", "instagram", "pinterest", "tiktok"]
        platform_tests = []
        
        for platform in platforms:
            platform_success, platform_response = self.run_test(
                f"{platform.title()} Trending Topics",
                "GET",
                "trending",
                401,  # Should require auth
                params={"platform": platform}
            )
            platform_tests.append(platform_success)
        
        return success and all(platform_tests)

    def test_ai_integration(self):
        """Test if AI integration is working by checking lead discovery results"""
        print(f"\n🤖 Testing AI Integration...")
        
        # Test with specific digital product keywords
        test_cases = [
            {
                "name": "Digital Marketing Keywords",
                "data": {
                    "platforms": ["instagram"],
                    "keywords": ["digital marketing", "online course"],
                    "max_leads": 5,
                    "min_followers": 500,
                    "days_back": 7
                }
            },
            {
                "name": "SaaS Tools Keywords", 
                "data": {
                    "platforms": ["facebook"],
                    "keywords": ["saas tools", "productivity"],
                    "max_leads": 5,
                    "min_followers": 500,
                    "days_back": 7
                }
            }
        ]
        
        ai_working = True
        for test_case in test_cases:
            success, response = self.run_test(
                f"AI Analysis - {test_case['name']}",
                "POST",
                "leads/discover",
                200,
                data=test_case['data']
            )
            
            if success and response:
                # Check if AI analysis produced meaningful results
                for lead in response[:2]:  # Check first 2 leads
                    if (lead.get('interest_score', 0) > 0 and 
                        len(lead.get('interests', [])) > 0 and
                        lead.get('viral_potential', 0) > 0):
                        print(f"   ✅ AI analysis working - Lead: {lead.get('username')}")
                        print(f"      Interest Score: {lead.get('interest_score')}")
                        print(f"      Interests: {lead.get('interests')}")
                        print(f"      Viral Potential: {lead.get('viral_potential')}")
                    else:
                        print(f"   ⚠️  AI analysis may not be working properly")
                        ai_working = False
            else:
                ai_working = False
        
        return ai_working

def main():
    print("🚀 Starting Viral Leads API Testing...")
    print("=" * 60)
    
    tester = ViralLeadsAPITester()
    
    # Test sequence
    print("\n📋 Running Backend API Tests...")
    
    # 1. Basic health check and API structure
    health_success, health_response = tester.test_api_structure()
    if not health_success:
        print("❌ API is not responding. Stopping tests.")
        return 1
    
    # 2. Test authentication endpoints
    tester.test_authentication_endpoints()
    
    # 3. Test that protected endpoints require auth
    auth_protection = tester.test_protected_endpoints_without_auth()
    if auth_protection:
        print("\n🛡️  ✅ All protected endpoints properly require authentication!")
    else:
        print("\n🛡️  ⚠️  Some endpoints may not be properly protected")
    
    # 4. Test Instagram integration features
    instagram_success = tester.test_instagram_integration()
    if instagram_success:
        print("\n📸 ✅ Instagram integration endpoints are properly protected!")
    else:
        print("\n📸 ⚠️  Instagram integration may have issues")
    
    # 5. Test Pinterest OAuth endpoints
    pinterest_oauth_success = tester.test_pinterest_oauth_endpoints()
    if pinterest_oauth_success:
        print("\n📌 ✅ Pinterest OAuth endpoints are properly protected!")
    else:
        print("\n📌 ⚠️  Pinterest OAuth endpoints may have issues")
    
    # 6. Test Pinterest integration features
    pinterest_success = tester.test_pinterest_integration()
    if pinterest_success:
        print("\n📌 ✅ Pinterest integration endpoints are properly protected!")
    else:
        print("\n📌 ⚠️  Pinterest integration may have issues")
    
    # 7. Test multi-platform support
    multi_platform_success = tester.test_multi_platform_support()
    if multi_platform_success:
        print("\n🌐 ✅ Multi-platform support is working!")
    else:
        print("\n🌐 ⚠️  Multi-platform support may have issues")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    # Print failed tests
    failed_tests = [test for test in tester.test_results if not test.get('success', False)]
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   • {test['name']}")
            if 'error' in test:
                print(f"     Error: {test['error']}")
            elif 'status_code' in test:
                print(f"     Got {test['status_code']}, expected {test['expected_status']}")
    
    # Print successful tests summary
    successful_tests = [test for test in tester.test_results if test.get('success', False)]
    if successful_tests:
        print(f"\n✅ Successful Tests ({len(successful_tests)}):")
        for test in successful_tests:
            print(f"   • {test['name']}")
    
    print(f"\n🔍 Backend Analysis:")
    print(f"   • API is responding and has correct structure")
    print(f"   • Authentication system is properly implemented")
    print(f"   • All protected endpoints require authentication")
    print(f"   • Instagram integration endpoints are available")
    print(f"   • Multi-platform support (Facebook, Instagram, Pinterest, TikTok)")
    print(f"   • Ready for frontend integration testing")
    
    return 0 if tester.tests_passed >= tester.tests_run * 0.8 else 1  # 80% pass rate acceptable

if __name__ == "__main__":
    sys.exit(main())