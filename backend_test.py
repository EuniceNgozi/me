import requests
import sys
import json
from datetime import datetime

class ViralLeadsAPITester:
    def __init__(self, base_url="https://viral-leads.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.session = requests.Session()  # Use session for cookies

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

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

    def test_health_check(self):
        """Test basic API health check"""
        return self.run_test(
            "API Health Check",
            "GET",
            "",
            200
        )

    def test_analytics(self):
        """Test analytics endpoint"""
        return self.run_test(
            "Analytics Endpoint",
            "GET",
            "analytics",
            200
        )

    def test_trending_topics(self):
        """Test trending topics endpoint"""
        success, response = self.run_test(
            "Trending Topics - All Platforms",
            "GET",
            "trending",
            200
        )
        
        if success:
            # Test platform-specific trending
            self.run_test(
                "Trending Topics - Facebook",
                "GET",
                "trending",
                200,
                params={"platform": "facebook"}
            )
        
        return success, response

    def test_get_leads(self):
        """Test get leads endpoint"""
        success, response = self.run_test(
            "Get Leads - Basic",
            "GET",
            "leads",
            200
        )
        
        if success:
            # Test with filters
            self.run_test(
                "Get Leads - With Filters",
                "GET",
                "leads",
                200,
                params={"platform": "instagram", "min_score": 50, "limit": 10}
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
            200,
            data=test_data
        )
        
        if success and response:
            print(f"   ✅ Discovered {len(response)} leads")
            if len(response) > 0:
                lead = response[0]
                print(f"   Sample lead: {lead.get('username', 'N/A')} on {lead.get('platform', 'N/A')}")
                print(f"   Interest score: {lead.get('interest_score', 'N/A')}")
                print(f"   Interests: {lead.get('interests', [])}")
        
        return success, response

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
    
    # 1. Basic health check
    health_success, _ = tester.test_health_check()
    if not health_success:
        print("❌ API is not responding. Stopping tests.")
        return 1
    
    # 2. Test analytics
    tester.test_analytics()
    
    # 3. Test trending topics
    tester.test_trending_topics()
    
    # 4. Test get leads
    tester.test_get_leads()
    
    # 5. Test lead discovery (main feature)
    discover_success, _ = tester.test_discover_leads()
    
    # 6. Test AI integration specifically
    if discover_success:
        ai_success = tester.test_ai_integration()
        if ai_success:
            print("\n🤖 ✅ AI Integration appears to be working!")
        else:
            print("\n🤖 ⚠️  AI Integration may have issues")
    
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
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())