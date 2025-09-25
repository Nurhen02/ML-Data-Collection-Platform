from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class JobStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SourceType(enum.Enum):
    NEWS = "NEWS"
    TWITTER = "TWITTER"
    REDDIT = "REDDIT"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    status = Column(String, default=JobStatus.PENDING.value)
    source_type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ScrapedData(Base):
    __tablename__ = "scraped_data"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    clean_text = Column(Text, nullable=True)
    page_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' to 'page_metadata'