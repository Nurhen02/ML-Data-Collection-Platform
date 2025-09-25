from celery import Celery
import os

# Use the REDIS_URL from environment variables, default to localhost
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create the Celery application instance
celery_app = Celery(
    "ml_worker",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks"]  # This tells Celery where to find your tasks
)

# Optional: Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)