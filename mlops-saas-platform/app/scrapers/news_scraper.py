from .scraper_base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class NewsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.request_delay = 3.0
    
    def scrape(self, url):
        try:
            # Fetch and parse the page
            response = self._fetch_url(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main content
            title = self._extract_title(soup)
            content = self._extract_content(soup)
            clean_text = self._clean_text(f"{title}\n\n{content}" if title else content)
            
            # Extract metadata and media
            metadata = self._extract_metadata(soup, url)
            image_urls = self._extract_image_urls(soup, url)
            video_info = self._extract_video_info(soup, url)
            engagement_metrics = self._extract_engagement_metrics(soup)
            
            # Add media information to metadata
            if image_urls:
                metadata['image_urls'] = image_urls
                metadata['image_count'] = len(image_urls)
            
            if video_info:
                metadata.update(video_info)
            
            # Add engagement metrics
            if engagement_metrics:
                metadata.update(engagement_metrics)
            
            return {
                'clean_text': clean_text,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"News scraper failed for {url}: {str(e)}")
            return self._create_error_response(url, str(e))
    
    def _extract_title(self, soup):
        """Extract article title using multiple strategies"""
        selectors = [
            'h1',
            'title',
            '[property="og:title"]',
            '[name="title"]',
            '[class*="title"]',
            '[id*="title"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title and len(title) > 10:
                    return title
        
        return "No title found"
    
    def _extract_content(self, soup):
        """Extract main article content"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'aside', 'header']):
            element.decompose()
        
        content_selectors = [
            'article',
            '[class*="content"]',
            '[class*="article"]',
            '[id*="content"]',
            '[id*="article"]',
            'main',
            '.story-body',
            '.post-content'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest content block
                content_elements = sorted(elements, key=lambda x: len(x.get_text()), reverse=True)
                if content_elements:
                    return content_elements[0].get_text()
        
        # Fallback: get all paragraphs
        paragraphs = soup.find_all('p')
        content = '\n'.join([p.get_text() for p in paragraphs if p.get_text().strip()])
        return content if content else soup.get_text()
    
    def _extract_metadata(self, soup, url):
        """Extract article metadata"""
        metadata = {
            'source_url': url,
            'source_type': 'NEWS',
            'domain': self.get_domain(url),
            'scraped_at': datetime.utcnow().isoformat(),
            'method': 'beautifulsoup'
        }
        
        # Extract publication date
        date = self._extract_date(soup)
        if date:
            metadata['publish_date'] = date
        
        # Extract author
        author = self._extract_author(soup)
        if author:
            metadata['author'] = author
        
        # Extract description
        description = self._extract_description(soup)
        if description:
            metadata['description'] = description
        
        # Extract category/tags
        categories = self._extract_categories(soup)
        if categories:
            metadata['categories'] = categories
            metadata['category_count'] = len(categories)
        
        # Extract reading time estimate
        reading_time = self._estimate_reading_time(soup)
        if reading_time:
            metadata['estimated_reading_time_minutes'] = reading_time
        
        return metadata
    
    def _extract_image_urls(self, soup, base_url):
        """Extract image URLs from article"""
        try:
            image_selectors = [
                'article img',
                '.article-content img',
                '.post-content img',
                'main img',
                '[class*="image"] img',
                'img[src*="/wp-content/"]'
            ]
            
            image_urls = []
            for selector in image_selectors:
                images = soup.select(selector)
                for img in images:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        # Convert relative URLs to absolute
                        full_url = urljoin(base_url, src)
                        if self._is_content_image(full_url):
                            image_urls.append(full_url)
            
            return list(set(image_urls))[:10]  # Limit to 10 images
            
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
            return []
    
    def _extract_video_info(self, soup, base_url):
        """Extract video information from article"""
        try:
            video_selectors = [
                'video',
                'iframe[src*="youtube"]',
                'iframe[src*="vimeo"]',
                '[class*="video"]'
            ]
            
            video_info = {}
            video_count = 0
            
            for selector in video_selectors:
                videos = soup.select(selector)
                if videos:
                    video_count += len(videos)
                    # Extract first video thumbnail if available
                    for video in videos[:1]:
                        thumbnail = video.get('poster') or video.get('data-thumbnail')
                        if thumbnail:
                            video_info['thumbnail_url'] = urljoin(base_url, thumbnail)
                            break
            
            if video_count > 0:
                video_info['has_video'] = True
                video_info['video_count'] = video_count
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            return {}
    
    def _extract_engagement_metrics(self, soup):
        """Extract engagement metrics like comments, shares"""
        try:
            metrics = {}
            
            # Look for comment count
            comment_selectors = [
                '[class*="comment"] [class*="count"]',
                '[class*="comment"] [class*="number"]',
                '.comment-count',
                '.comments-number'
            ]
            
            for selector in comment_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text().strip()
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        metrics['comment_count'] = int(numbers[0])
                        break
            
            # Look for share count
            share_selectors = [
                '[class*="share"] [class*="count"]',
                '[class*="share"] [class*="number"]',
                '.share-count',
                '.shares-number'
            ]
            
            for selector in share_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text().strip()
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        metrics['share_count'] = int(numbers[0])
                        break
            
            # Look for view count
            view_selectors = [
                '[class*="view"] [class*="count"]',
                '[class*="view"] [class*="number"]',
                '.view-count',
                '.views-number'
            ]
            
            for selector in view_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text().strip()
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        metrics['view_count'] = int(numbers[0])
                        break
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error extracting engagement metrics: {str(e)}")
            return {}
    
    def _extract_date(self, soup):
        """Extract publication date"""
        date_selectors = [
            '[property="article:published_time"]',
            '[name="publish_date"]',
            'time[datetime]',
            '[class*="date"]',
            '[class*="time"]',
            '.published',
            '.date-published'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_str = element.get('content') or element.get('datetime') or element.get_text()
                if date_str:
                    return date_str.strip()
        return None
    
    def _extract_author(self, soup):
        """Extract author information"""
        author_selectors = [
            '[property="article:author"]',
            '[name="author"]',
            '[class*="author"]',
            '.byline',
            '.author-name',
            '.post-author'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get('content') or element.get_text()
                if author:
                    return author.strip()
        return None
    
    def _extract_description(self, soup):
        """Extract article description"""
        description_selectors = [
            '[property="og:description"]',
            '[name="description"]',
            '[class*="description"]',
            '.article-description',
            '.post-excerpt'
        ]
        
        for selector in description_selectors:
            element = soup.select_one(selector)
            if element:
                description = element.get('content') or element.get_text()
                if description:
                    return description.strip()
        return None
    
    def _extract_categories(self, soup):
        """Extract categories or tags"""
        category_selectors = [
            '[class*="category"] a',
            '[class*="tag"] a',
            '.post-categories a',
            '.article-tags a'
        ]
        
        categories = []
        for selector in category_selectors:
            elements = soup.select(selector)
            for element in elements:
                category = element.get_text().strip()
                if category and category not in categories:
                    categories.append(category)
        
        return categories if categories else None
    
    def _estimate_reading_time(self, soup):
        """Estimate reading time based on word count"""
        try:
            text_content = soup.get_text()
            word_count = len(text_content.split())
            reading_time = max(1, word_count // 200)  # 200 words per minute
            return reading_time
        except:
            return None
    
    def _is_content_image(self, url):
        """Check if URL is likely a content image (not icon/logo)"""
        excluded_terms = ['logo', 'icon', 'avatar', 'spinner', 'loading']
        return (any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and
                not any(term in url.lower() for term in excluded_terms))
    
    def _create_error_response(self, url, error_message):
        """Create a response when scraping fails"""
        return {
            'clean_text': f"Error: Could not scrape news content from {url}. Reason: {error_message}",
            'metadata': {
                'source_url': url,
                'source_type': 'NEWS',
                'error': error_message,
                'scraped_at': datetime.utcnow().isoformat()
            }
        }