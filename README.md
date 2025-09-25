# MLOps Data Collection Platform

A professional SaaS platform that automatically collects and processes web data for machine learning applications.

## What This Platform Does

This system allows you to submit URLs from various websites and receive clean, structured data perfect for training machine learning models. It handles the entire process automatically:

- **Accepts URLs** from news sites, Twitter/X, Reddit, and other websites
- **Extracts content** including text, images, videos, and engagement metrics
- **Cleans and structures** the data for immediate ML use
- **Provides a simple API** and web interface for easy access

## System Architecture

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Browser  │    │   FastAPI Server │    │  PostgreSQL DB  │
│                 │    │   (Python)       │    │   (Jobs Table)  │
│ - Submit URL    │◄──►│ - REST API       │◄──►│ - Job metadata  │
│ - View Results  │    │ - Validation     │    │ - Status tracking│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         │              ┌────────┴────────┐              │
         │              │                 │              │
         │        ┌─────▼─────┐    ┌─────▼─────┐         │
         │        │  Redis    │    │ Celery    │         │
         │        │  Queue    │    │  Workers  │         │
         │        │           │    │ (Python)  │         │
         │        └─────┬─────┘    └─────┬─────┘         │
         │              │                 │              │
         │              └─────┬─────┬─────┘              │
         │                    │     │                    │
         │              ┌─────▼─────▼─────┐              │
         │              │   Scrapers      │              │
         │              │   (Python)      │              │
         │              └─────┬─────┬─────┘              │
         │                    │     │                    │
┌─────────────────┐    ┌─────▼─────▼─────┐    ┌─────────▼────────┐
│   External      │    │  PostgreSQL DB  │    │   FastAPI Server │
│   Sources       │    │ (Scraped Data)  │    │   (Response)     │
│ - News sites    │◄──►│ - Clean text    │◄──►│ - Return results │
│ - Twitter/X     │    │ - Metadata      │    │ - JSON format    │
│ - Reddit        │    │ - ML-ready      │    └──────────────────┘
└─────────────────┘    └─────────────────┘

1-Start with User Input: "Users submit URLs through a web interface"

2- API Layer: "FastAPI validates the input and creates a job record"

3- Async Processing: "Instead of making users wait, we queue the job in Redis"

4- Background Workers: "Celery workers process jobs in the background using specialized scrapers"

5- Data Storage: "Results are stored in PostgreSQL with clean text and rich metadata"

6- Completion: "Users can check status and retrieve ML-ready data via API"


## Key Components:
- **Frontend**: Modern web interface for submitting URLs and viewing results
- **FastAPI Server**: Handles API requests and serves the frontend
- **PostgreSQL Database**: Stores all jobs and processed data
- **Redis Queue**: Manages background job processing
- **Celery Workers**: Perform the actual scraping work
- **Specialized Scrapers**: Different tools for different website types

## Installation & Quick Start

## Prerequisites:
- Docker and Docker Compose installed
- 4GB of available RAM
- Windows (Windows users need WSL2)

## 3-Step Setup:

1. **Start the platform**
   ```bash
   docker-compose up --build

2. **Access the application**
- Web Interface: http://localhost:8000

- API Documentation: http://localhost:8000/docs   

3. **Test with sample URLs**
- News: https://www.bbc.com/news/world-us-canada-12345678

- Twitter: https://x.com/GlobeEyeNews/status/1969842243214475493

- Reddit: Any public Reddit post URL

## API Usage Examples

1. **Submit a New Scraping Job**

1- 
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "source_type": "NEWS"
  }'
2- Response:
{
  "id": 1,
  "url": "https://example.com/article",
  "status": "PENDING",
  "source_type": "NEWS",
  "created_at": "2023-10-27T10:30:00.123456"
}  

2. **Check Job Status**
curl "http://localhost:8000/jobs/1"

3. **Get Scraped Data**
curl "http://localhost:8000/data/1"

Sample Response:

{
  "id": 1,
  "job_id": 1,
  "clean_text": "This is the cleaned article content...",
  "page_metadata": {
    "title": "Article Title",
    "author": "John Doe",
    "publish_date": "2023-10-27",
    "images": ["url1", "url2"],
    "engagement_metrics": {
      "likes": 150,
      "shares": 45
    }
  }
}

4. **Interactive API Documentation**
Visit http://localhost:8000/docs for Swagger UI with live testing.

## Configuration Options

1. **Environment Variables**

## Environment Variables

This project uses environment variables to configure databases, caching, and external APIs.

1. **Database (PostgreSQL)**

- POSTGRES_DB → Name of the database (default: saasdb)

- POSTGRES_USER → Database username (default: postgres)

- POSTGRES_PASSWORD → Database password (default: postgres)

 -DATABASE_URL → Full connection string used by the app (postgresql://user:password@db:5432/dbname)

2. **Task Queue / Caching (Redis)**

- REDIS_URL → Redis connection string (default: redis://redis:6379/0)

- Reddit API (Optional)

- REDDIT_CLIENT_ID → Reddit app client ID

- REDDIT_CLIENT_SECRET → Reddit app client secret

- REDDIT_USER_AGENT → User agent string for Reddit API

3. **Security**
- SECRET_KEY → Secret key for JWT tokens

- DEBUG → Set to "False" in production

- CORS_ORIGINS → Allowed domains for API requests

4. **Development vs Production**

- Development: Uses defaults in docker-compose.yml.

- Production: Change passwords, secrets, and API keys to secure values.


5. **Sample Data & Test URLs**

The system works with these types of URLs:

- News Articles: BBC, Reuters, NY Times blogs

- Social Media: Twitter/X posts, Reddit threads

- General Websites: Any public webpage with text content

## Current Limitations

- **JavaScript Requirements**: Some modern sites need JavaScript rendering (handled automatically)

- **Rate Limiting**: Built-in delays to respect website policies

- **Authentication**: Public content only - no login-required sites

- **Legal Compliance:** Users must respect website terms of service
