from .celery_worker import celery_app
from .database import SessionLocal
from . import models
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
from requests.exceptions import RequestException, Timeout, ConnectionError

# Set up logging
logger = logging.getLogger(__name__)

# Retry configuration for network requests
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RequestException, Timeout, ConnectionError)),
)
def fetch_url_with_retry(url, timeout=10):
    """Fetch URL with retry logic for network issues"""
    response = requests.get(url, timeout=timeout, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    response.raise_for_status()
    return response

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def scrape_url_task(self, job_id):
    db = SessionLocal()
    job = None
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = models.JobStatus.PROCESSING.value
        db.commit()
        
        scraper = get_scraper_for_url(job.url, job.source_type)
        result = scraper.scrape(job.url)
        
        # Check if scraping actually failed
        if "Error:" in result['clean_text']:
            job.status = models.JobStatus.FAILED.value
            job.error_message = result['clean_text']
        else:
            scraped_data = models.ScrapedData(
                job_id=job_id,
                clean_text=result['clean_text'],
                page_metadata=result['metadata']
            )
            db.add(scraped_data)
            job.status = models.JobStatus.COMPLETED.value
        
        db.commit()
        
    except Exception as e:
        if job:
            job.status = models.JobStatus.FAILED.value
            job.error_message = str(e)
            db.commit()
        self.retry(exc=e, countdown=300)  # Longer delay for retries
    finally:
        db.close()

def get_scraper_for_url(url, source_type):
    """Factory function to get the appropriate scraper"""
    if source_type == "NEWS" or "news" in url:
        from .scrapers.news_scraper import NewsScraper
        return NewsScraper()
    elif source_type == "TWITTER" or "twitter.com" in url or "x.com" in url:
        from .scrapers.twitter_scraper import TwitterScraper
        return TwitterScraper()
    elif source_type == "REDDIT" or "reddit.com" in url:
        from .scrapers.reddit_scraper import RedditScraper
        return RedditScraper()
    else:
        from .scrapers.general_scraper import GeneralScraper
        return GeneralScraper()

    