from abc import ABC, abstractmethod
import time
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self):
        self.last_request_time = 0
        self.request_delay = 2.0  # Minimum delay between requests in seconds
        
    def _respect_rate_limit(self):
        """Ensure we respect rate limiting by delaying requests"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_url(self, url, timeout=10):
        """Fetch URL with retry logic and proper headers"""
        self._respect_rate_limit()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {str(e)}")
            raise
    
    def _clean_text(self, text):
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        return text
    
    @abstractmethod
    def scrape(self, url):
        """Main method to be implemented by specific scrapers"""
        pass
    
    def get_domain(self, url):
        """Extract domain from URL"""
        return urlparse(url).netloc