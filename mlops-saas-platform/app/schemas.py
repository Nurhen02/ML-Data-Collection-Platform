from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

# Enum for job status (similar to the SQLAlchemy enum)
class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# Schema for creating a new job (used in POST /jobs request)
class JobCreate(BaseModel):
    url: HttpUrl  # Validates that the input is a valid URL
    source_type: Optional[str] = None  # Optional field for source type (e.g., "NEWS")

# Schema for responding with job status (used in GET /jobs/{job_id} response)
class JobStatusResponse(BaseModel):
    id: int
    url: str
    status: JobStatus
    source_type: Optional[str] = None
    created_at: datetime

    # This allows SQLAlchemy models to be converted to Pydantic models
    class Config:
        from_attributes = True

# Schema for responding with scraped data (used in GET /data/{job_id} response)
class DataResponse(BaseModel):
    id: int
    job_id: int
    clean_text: Optional[str] = None
    page_metadata: Optional[Dict[str, Any]] = None  # Flexible JSON field for metadata

    class Config:
        from_attributes = True