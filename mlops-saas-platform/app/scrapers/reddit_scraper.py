from .scraper_base import BaseScraper
import praw
from datetime import datetime
import logging
import os
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class RedditScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.request_delay = 3.0
        self.reddit = None
        self._initialize_reddit()
    
    def _initialize_reddit(self):
        """Initialize Reddit API client if credentials are available"""
        try:
            client_id = os.getenv('REDDIT_CLIENT_ID')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            user_agent = os.getenv('REDDIT_USER_AGENT', 'mlops-saas-platform by /u/your_username')
            
            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )
                logger.info("Reddit API client initialized successfully")
            else:
                logger.warning("Reddit API credentials not found. Using limited functionality.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Reddit API: {str(e)}")
    
    def scrape(self, url):
        try:
            if self.reddit:
                return self._scrape_with_api(url)
            else:
                return self._scrape_without_api(url)
                
        except Exception as e:
            logger.error(f"Reddit scraper failed for {url}: {str(e)}")
            return self._create_error_response(url, str(e))
    
    def _scrape_with_api(self, url):
        """Scrape Reddit content using the official API"""
        submission = self.reddit.submission(url=url)
        
        # Extract main content
        title = submission.title
        selftext = submission.selftext
        clean_text = self._clean_text(f"{title}\n\n{selftext}" if selftext else title)
        
        # Extract comments
        submission.comments.replace_more(limit=0)
        comments = []
        for comment in submission.comments.list()[:10]:  # Limit to 10 comments
            if len(comment.body) < 1000:
                comments.append(comment.body)
        
        if comments:
            clean_text += "\n\nTop Comments:\n" + "\n".join([f"- {c}" for c in comments])
        
        # Extract metadata
        metadata = self._extract_metadata(submission, url)
        
        # Extract media information
        image_urls = self._extract_image_urls(submission)
        video_info = self._extract_video_info(submission)
        
        # Add media to metadata
        if image_urls:
            metadata['image_urls'] = image_urls
            metadata['image_count'] = len(image_urls)
        
        if video_info:
            metadata.update(video_info)
        
        # Engagement metrics are already included in base metadata
        
        return {
            'clean_text': clean_text,
            'metadata': metadata
        }
    
    def _scrape_without_api(self, url):
        """Fallback method when API credentials aren't available"""
        try:
            response = self._fetch_url(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Basic scraping without API
            title = soup.find('h1')
            title_text = title.get_text().strip() if title else "No title found"
            
            content = soup.get_text()
            clean_text = self._clean_text(content)
            
            metadata = {
                'source_url': url,
                'source_type': 'REDDIT',
                'domain': self.get_domain(url),
                'scraped_at': datetime.utcnow().isoformat(),
                'method': 'basic_fallback',
                'note': 'API credentials not configured - limited data available'
            }
            
            return {
                'clean_text': clean_text,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Fallback scraping failed: {str(e)}")
            return self._create_error_response(url, "All scraping methods failed")
    
    def _extract_metadata(self, submission, url):
        """Extract comprehensive metadata from Reddit submission"""
        metadata = {
            'source_url': url,
            'source_type': 'REDDIT',
            'domain': self.get_domain(url),
            'scraped_at': datetime.utcnow().isoformat(),
            'method': 'praw_api',
            'title': submission.title,
            'subreddit': str(submission.subreddit),
            'author': str(submission.author) if submission.author else 'unknown',
            'upvotes': submission.score,
            'num_comments': submission.num_comments,
            'created_utc': datetime.utcfromtimestamp(submission.created_utc).isoformat(),
            'nsfw': submission.over_18,
            'post_id': submission.id,
            'permalink': submission.permalink,
            'url': submission.url,
            'domain': submission.domain
        }
        
        # Additional engagement metrics
        if hasattr(submission, 'upvote_ratio'):
            metadata['upvote_ratio'] = submission.upvote_ratio
        
        if hasattr(submission, 'total_awards_received'):
            metadata['award_count'] = submission.total_awards_received
        
        # Flair information
        if submission.link_flair_text:
            metadata['flair'] = submission.link_flair_text
        
        # Post type
        if submission.is_self:
            metadata['post_type'] = 'text'
        else:
            metadata['post_type'] = 'link'
        
        return metadata
    
    def _extract_image_urls(self, submission):
        """Extract image URLs from Reddit post"""
        image_urls = []
        
        # Check if post has gallery
        if hasattr(submission, 'is_gallery') and submission.is_gallery:
            try:
                for item in submission.gallery_data['items']:
                    media_id = item['media_id']
                    metadata = submission.media_metadata[media_id]
                    if metadata['status'] == 'valid':
                        image_urls.append(metadata['s']['u'])
            except:
                pass
        
        # Check for preview images
        if hasattr(submission, 'preview') and submission.preview:
            try:
                images = submission.pview['images']
                for image in images:
                    image_urls.append(image['source']['url'])
            except:
                pass
        
        # Check thumbnail
        if submission.thumbnail and submission.thumbnail not in ['self', 'default', 'nsfw']:
            image_urls.append(submission.thumbnail)
        
        return list(set(image_urls))
    
    def _extract_video_info(self, submission):
        """Extract video information from Reddit post"""
        video_info = {}
        
        # Check for video
        if hasattr(submission, 'is_video') and submission.is_video:
            video_info['has_video'] = True
            
            # Try to get video URL
            if hasattr(submission, 'media') and submission.media:
                try:
                    if 'reddit_video' in submission.media:
                        video_info['video_url'] = submission.media['reddit_video']['fallback_url']
                        video_info['duration_seconds'] = submission.media['reddit_video']['duration']
                except:
                    pass
            
            # Try to get thumbnail
            if hasattr(submission, 'thumbnail') and submission.thumbnail:
                video_info['thumbnail_url'] = submission.thumbnail
        
        return video_info
    
    def _create_error_response(self, url, error_message):
        """Create a response when scraping fails"""
        return {
            'clean_text': f"Error: Could not scrape Reddit content from {url}. Reason: {error_message}",
            'metadata': {
                'source_url': url,
                'source_type': 'REDDIT',
                'error': error_message,
                'scraped_at': datetime.utcnow().isoformat()
            }
        }