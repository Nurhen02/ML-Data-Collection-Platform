from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from . import models, schemas
from .database import get_db
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="ML Data Collection API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="app/frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Serve the main HTML file
    with open("app/frontend/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

# Your existing API endpoints
@app.post("/jobs", response_model=schemas.JobStatusResponse)
async def create_job(job: schemas.JobCreate, db: Session = Depends(get_db)):
    db_job = models.Job(url=str(job.url), source_type=job.source_type)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    from .tasks import scrape_url_task
    scrape_url_task.delay(db_job.id)
    
    return db_job

@app.get("/jobs/{job_id}", response_model=schemas.JobStatusResponse)
async def get_job_status(job_id: int, db: Session = Depends(get_db)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

@app.get("/data/{job_id}", response_model=schemas.DataResponse)
async def get_job_data(job_id: int, db: Session = Depends(get_db)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if db_job.status != models.JobStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    db_data = db.query(models.ScrapedData).filter(models.ScrapedData.job_id == job_id).first()
    if not db_data:
        raise HTTPException(status_code=404, detail="Data not found")
    
    return db_data