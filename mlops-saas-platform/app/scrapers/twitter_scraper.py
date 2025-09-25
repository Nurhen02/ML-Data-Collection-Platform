from .scraper_base import BaseScraper
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

class TwitterScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.request_delay = 15.0
    
    def scrape(self, url):
        try:
            # Use Playwright with more realistic browser behavior
            content, screenshot_path, image_urls, video_info, engagement_metrics = self._scrape_with_playwright(url)
            
            if content and not self._is_login_wall(content):
                clean_text = self._clean_text(content)
                metadata = self._extract_metadata(url, content)
                metadata['screenshot_path'] = screenshot_path
                
                # Add media information
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
            else:
                # Fallback to API if available
                return self._fallback_scrape(url)
                
        except Exception as e:
            logger.error(f"Twitter scraper failed for {url}: {str(e)}")
            return self._create_error_response(url, str(e))
    
    def _scrape_with_playwright(self, url):
        """Use Playwright with enhanced stealth and waiting"""
        with sync_playwright() as p:
            try:
                # Launch browser with stealth options
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    java_script_enabled=True
                )
                
                # Block unnecessary resources to speed up loading
                context.route("**/*.{png,jpg,jpeg,webp,gif,css,woff,woff2}", lambda route: route.abort())
                
                page = context.new_page()
                
                # Navigate to the URL
                page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Wait for specific tweet content to load
                page.wait_for_selector('[data-testid="tweetText"]', timeout=30000)
                
                # Additional wait for content to render
                time.sleep(5)
                
                # Extract tweet content
                tweet_content = self._extract_tweet_text(page)
                
                # Extract image URLs
                image_urls = self._extract_image_urls(page)
                
                # Extract video information
                video_info = self._extract_video_info(page)
                
                # Extract engagement metrics
                engagement_metrics = self._extract_engagement_metrics(page)
                
                # Take screenshot for debugging
                screenshot_path = f"/tmp/twitter_screenshot_{int(time.time())}.png"
                page.screenshot(path=screenshot_path, full_page=True)
                
                browser.close()
                return tweet_content, screenshot_path, image_urls, video_info, engagement_metrics
                
            except Exception as e:
                logger.error(f"Playwright failed for {url}: {str(e)}")
                if 'browser' in locals():
                    browser.close()
                return None, None, [], {}, {}
    
    def _extract_tweet_text(self, page):
        """Extract tweet text content"""
        tweet_selectors = [
            '[data-testid="tweetText"]',
            'article div[lang]',
            '[role="article"]',
            'div[data-testid="cellInnerDiv"]',
            'div[lang].css-1rynq56'
        ]
        
        tweet_content = None
        for selector in tweet_selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    content_parts = []
                    for element in elements:
                        text = element.inner_text()
                        if text and len(text.strip()) > 20:
                            content_parts.append(text.strip())
                    
                    if content_parts:
                        tweet_content = "\n\n".join(content_parts)
                        break
            except:
                continue
        
        # If we couldn't find specific content, try to get page text
        if not tweet_content:
            tweet_content = page.inner_text('body')
        
        return tweet_content
    
    def _extract_image_urls(self, page):
        """Extract image URLs from tweet"""
        try:
            image_selectors = [
                '[data-testid="tweetPhoto"] img',
                'div[data-testid="card.layoutLarge.media"] img',
                'article img[src*="twimg.com"]'
            ]
            
            image_urls = []
            for selector in image_selectors:
                images = page.query_selector_all(selector)
                for img in images:
                    src = img.get_attribute('src')
                    if src and 'http' in src and 'profile_images' not in src:
                        # Convert to higher quality if possible
                        high_quality_src = src.replace('&name=small', '&name=large')
                        image_urls.append(high_quality_src)
            
            return list(set(image_urls))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
            return []
    
    def _extract_video_info(self, page):
        """Extract video information from tweet"""
        try:
            video_selectors = [
                '[data-testid="videoComponent"]',
                'video',
                '[data-testid="tweetVideo"]'
            ]
            
            video_info = {}
            for selector in video_selectors:
                video_elements = page.query_selector_all(selector)
                if video_elements:
                    video_info['has_video'] = True
                    # Try to get video thumbnail
                    first_video = video_elements[0]
                    thumbnail = first_video.get_attribute('poster')
                    if thumbnail:
                        video_info['thumbnail_url'] = thumbnail
                    break
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            return {}
    
    def _extract_engagement_metrics(self, page):
        """Extract likes, retweets, replies, etc."""
        try:
            metrics = {}
            
            # Selectors for engagement metrics
            metric_selectors = {
                'likes': '[data-testid="like"] span',
                'retweets': '[data-testid="retweet"] span', 
                'replies': '[data-testid="reply"] span',
                'views': '[data-testid="app-text-transition-container"] span'
            }
            
            for metric, selector in metric_selectors.items():
                elements = page.query_selector_all(selector)
                if elements:
                    # Get the last element which usually contains the count
                    text = elements[-1].inner_text().strip()
                    # Extract numbers (handle K, M suffixes)
                    numbers = re.findall(r'[\d.,]+[KkMm]?', text)
                    if numbers:
                        metrics[metric] = numbers[0]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error extracting engagement metrics: {str(e)}")
            return {}
    
    def _is_login_wall(self, content):
        """Check if we hit a login/consent wall"""
        login_indicators = [
            "Don't miss what's happening",
            "People on X are the first to know",
            "Log in",
            "Sign up",
            "See new posts",
            "To view this content, please"
        ]
        
        return any(indicator in content for indicator in login_indicators)
    
    def _extract_metadata(self, url, content):
        """Extract metadata from Twitter content"""
        metadata = {
            'source_url': url,
            'source_type': 'TWITTER',
            'domain': self.get_domain(url),
            'scraped_at': datetime.utcnow().isoformat(),
            'method': 'playwright_enhanced'
        }
        
        # Extract engagement metrics from text as fallback
        engagement = self._extract_engagement_metrics_from_text(content)
        if engagement:
            metadata.update(engagement)
        
        return metadata
    
    def _extract_engagement_metrics_from_text(self, content):
        """Extract metrics from text content as fallback"""
        metrics = {}
        
        patterns = {
            'likes': r'(\d+(\.\d+)?[KkMm]?)\s*Likes',
            'retweets': r'(\d+(\.\d+)?[KkMm]?)\s*Retweets',
            'replies': r'(\d+(\.\d+)?[KkMm]?)\s*Replies',
            'views': r'(\d+(\.\d+)?[KkMm]?)\s*Views'
        }
        
        for metric, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                metrics[metric] = match.group(1)
        
        return metrics
    
    def _fallback_scrape(self, url):
        """Fallback method using alternative approaches"""
        try:
            # Try using snscrape as fallback
            import snscrape.modules.twitter as sntwitter
            
            tweet_id = self._extract_tweet_id(url)
            if tweet_id:
                scraper = sntwitter.TwitterTweetScraper(tweetId=tweet_id)
                
                for tweet in scraper.get_items():
                    if tweet:
                        metadata = {
                            'source_url': url,
                            'source_type': 'TWITTER',
                            'tweet_id': tweet.id,
                            'date': tweet.date.isoformat() if tweet.date else datetime.utcnow().isoformat(),
                            'likes': tweet.likeCount,
                            'retweets': tweet.retweetCount,
                            'method': 'snscrape_fallback'
                        }
                        
                        # Try to extract additional metrics if available
                        if hasattr(tweet, 'replyCount'):
                            metadata['replies'] = tweet.replyCount
                        if hasattr(tweet, 'quoteCount'):
                            metadata['quotes'] = tweet.quoteCount
                        if hasattr(tweet, 'viewCount'):
                            metadata['views'] = tweet.viewCount
                        
                        return {
                            'clean_text': tweet.rawContent,
                            'metadata': metadata
                        }
        except Exception as e:
            logger.warning(f"Fallback scraping also failed: {str(e)}")
        
        return self._create_error_response(url, "All scraping methods failed")
    
    def _extract_tweet_id(self, url):
        """Extract tweet ID from URL"""
        patterns = [
            r'twitter\.com/\w+/status/(\d+)',
            r'x\.com/\w+/status/(\d+)',
            r'twitter\.com/i/web/status/(\d+)',
            r'x\.com/i/web/status/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _create_error_response(self, url, error_message):
        """Create a response when scraping fails"""
        return {
            'clean_text': f"Error: Could not scrape Twitter/X content from {url}. Reason: {error_message}",
            'metadata': {
                'source_url': url,
                'source_type': 'TWITTER',
                'error': error_message,
                'scraped_at': datetime.utcnow().isoformat(),
                'note': 'Twitter/X may require authentication or may be blocking automated access'
            }
        }