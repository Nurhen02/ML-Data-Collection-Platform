#!/usr/bin/env python3
"""
API Test Script for MLOps SaaS Platform
Tests all endpoints with sample data
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class MLPlatformTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def print_result(self, test_name: str, success: bool, response=None):
        """Print test results in a formatted way"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if response is not None and not success:
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
    
    def test_health_check(self) -> bool:
        """Test that the API is running"""
        try:
            response = self.session.get(f"{self.base_url}/")
            success = response.status_code == 200
            self.print_result("Health Check", success, response)
            return success
        except Exception as e:
            print(f"❌ Health Check - Connection failed: {e}")
            return False
    
    def test_api_docs(self) -> bool:
        """Test that API documentation is available"""
        try:
            response = self.session.get(f"{self.base_url}/docs")
            success = response.status_code == 200
            self.print_result("API Documentation", success, response)
            return success
        except Exception as e:
            print(f"❌ API Documentation - Connection failed: {e}")
            return False
    
    def submit_test_job(self, url: str, source_type: str = None) -> Dict[str, Any]:
        """Submit a job and return the job data"""
        payload = {"url": url}
        if source_type:
            payload["source_type"] = source_type
            
        response = self.session.post(
            f"{self.base_url}/jobs",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Job submission failed: {response.status_code} - {response.text}")
    
    def wait_for_job_completion(self, job_id: int, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a job to complete with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check job status
            status_response = self.session.get(f"{self.base_url}/jobs/{job_id}")
            if status_response.status_code != 200:
                raise Exception(f"Failed to get job status: {status_response.text}")
            
            job_data = status_response.json()
            status = job_data["status"]
            
            print(f"   Job {job_id} status: {status}")
            
            if status == "COMPLETED":
                return job_data
            elif status == "FAILED":
                raise Exception(f"Job {job_id} failed")
            
            # Wait before polling again
            time.sleep(5)
        
        raise Exception(f"Job {job_id} timed out after {timeout} seconds")
    
    def test_news_scraping(self) -> bool:
        """Test scraping a news website"""
        try:
            print("\n📰 Testing News Scraping...")
            
            # Submit a job for a news article
            job = self.submit_test_job(
                "https://www.bbc.com/news/world-us-canada-12345678",
                "NEWS"
            )
            
            job_id = job["id"]
            print(f"   Submitted job {job_id} for news scraping")
            
            # Wait for completion
            completed_job = self.wait_for_job_completion(job_id)
            
            # Get the scraped data
            data_response = self.session.get(f"{self.base_url}/data/{job_id}")
            if data_response.status_code == 200:
                scraped_data = data_response.json()
                print(f"   Successfully scraped {len(scraped_data.get('clean_text', ''))} characters")
                
                self.print_result("News Scraping", True)
                return True
            else:
                self.print_result("News Scraping", False, data_response)
                return False
                
        except Exception as e:
            print(f"❌ News Scraping Test Failed: {e}")
            return False
    
    def test_twitter_scraping(self) -> bool:
        """Test scraping a Twitter/X URL"""
        try:
            print("\n🐦 Testing Twitter/X Scraping...")
            
            # Use a real Twitter/X URL (this is a public tweet)
            job = self.submit_test_job(
                "https://x.com/GlobeEyeNews/status/1969842243214475493",
                "TWITTER"
            )
            
            job_id = job["id"]
            print(f"   Submitted job {job_id} for Twitter scraping")
            
            # Wait for completion (Twitter can take longer due to JavaScript rendering)
            completed_job = self.wait_for_job_completion(job_id, timeout=120)
            
            # Get the scraped data
            data_response = self.session.get(f"{self.base_url}/data/{job_id}")
            if data_response.status_code == 200:
                scraped_data = data_response.json()
                
                # Check if we got meaningful content (not just error messages)
                clean_text = scraped_data.get('clean_text', '')
                if clean_text and not clean_text.startswith("Error:"):
                    print(f"   Successfully scraped Twitter content")
                    self.print_result("Twitter Scraping", True)
                    return True
                else:
                    print(f"   Twitter scraping returned error: {clean_text}")
                    self.print_result("Twitter Scraping", False)
                    return False
            else:
                self.print_result("Twitter Scraping", False, data_response)
                return False
                
        except Exception as e:
            print(f"❌ Twitter Scraping Test Failed: {e}")
            return False
    
    def test_reddit_scraping(self) -> bool:
        """Test scraping a Reddit URL"""
        try:
            print("\n📝 Testing Reddit Scraping...")
            
            # Use a real Reddit URL
            job = self.submit_test_job(
                "https://www.reddit.com/r/learnprogramming/comments/abc123/sample_post/",
                "REDDIT"
            )
            
            job_id = job["id"]
            print(f"   Submitted job {job_id} for Reddit scraping")
            
            # Wait for completion
            completed_job = self.wait_for_job_completion(job_id)
            
            # Get the scraped data
            data_response = self.session.get(f"{self.base_url}/data/{job_id}")
            if data_response.status_code == 200:
                scraped_data = data_response.json()
                print(f"   Reddit scraping completed")
                self.print_result("Reddit Scraping", True)
                return True
            else:
                self.print_result("Reddit Scraping", False, data_response)
                return False
                
        except Exception as e:
            print(f"❌ Reddit Scraping Test Failed: {e}")
            return False
    
    def test_general_scraping(self) -> bool:
        """Test scraping a general website"""
        try:
            print("\n🌐 Testing General Website Scraping...")
            
            # Use a simple website
            job = self.submit_test_job("https://example.com")
            
            job_id = job["id"]
            print(f"   Submitted job {job_id} for general scraping")
            
            # Wait for completion
            completed_job = self.wait_for_job_completion(job_id)
            
            # Get the scraped data
            data_response = self.session.get(f"{self.base_url}/data/{job_id}")
            if data_response.status_code == 200:
                scraped_data = data_response.json()
                print(f"   Successfully scraped {len(scraped_data.get('clean_text', ''))} characters")
                self.print_result("General Scraping", True)
                return True
            else:
                self.print_result("General Scraping", False, data_response)
                return False
                
        except Exception as e:
            print(f"❌ General Scraping Test Failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling with invalid URL"""
        try:
            print("\n⚠️ Testing Error Handling...")
            
            # Submit an invalid URL
            response = self.session.post(
                f"{self.base_url}/jobs",
                json={"url": "not-a-valid-url"},
                headers={"Content-Type": "application/json"}
            )
            
            # Should return 422 Unprocessable Entity
            success = response.status_code == 422
            self.print_result("Error Handling", success, response)
            return success
                
        except Exception as e:
            print(f"❌ Error Handling Test Failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests and return overall success"""
        print("🚀 Starting MLOps SaaS Platform API Tests")
        print("=" * 50)
        
        tests = [
            self.test_health_check,
            self.test_api_docs,
            self.test_error_handling,
            self.test_general_scraping,
            self.test_news_scraping,
            self.test_twitter_scraping,
            self.test_reddit_scraping,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
                results.append(False)
            
            print()  # Add spacing between tests
        
        # Summary
        print("=" * 50)
        passed = sum(results)
        total = len(results)
        
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! The platform is working correctly.")
        else:
            print("❌ Some tests failed. Check the logs above for details.")
        
        return passed == total

def main():
    """Main function to run tests"""
    # Get base URL from command line or use default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    tester = MLPlatformTester(base_url)
    
    if not tester.run_all_tests():
        sys.exit(1)  # Exit with error code if tests fail

if __name__ == "__main__":
    main()