from .scraper_base import BaseScraper
from bs4 import BeautifulSoup

class GeneralScraper(BaseScraper):
    def scrape(self, url):
        # Simple fallback scraper for any website
        response = self._fetch_url(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'aside']):
            element.decompose()
        
        # Get all text content
        text = soup.get_text()
        clean_text = self._clean_text(text)
        
        return {
            'clean_text': clean_text,
            'metadata': {
                'source_url': url,
                'source_type': 'GENERAL',
                'domain': self.get_domain(url)
            }
        }