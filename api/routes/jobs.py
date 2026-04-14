# ~/benchmaster/api/routes/jobs.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from db.models import get_engine, get_session, BenchmarkJob, Machine, Result
from pydantic import BaseModel
from api.dependencies import verify_agent_token

router = APIRouter()

# --- Pydantic Models for Request/Response ---

class JobCreate(BaseModel):
    machine_id: int
    benchmark: str

class JobResponse(BaseModel):
    id: int
    machine_id: int
    benchmark: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Dependencies ---

def get_db_session():
    engine = get_engine()
    session = get_session(engine)
    try:
        yield session
    finally:
        session.close()

# --- Routes ---

@router.post("/", response_model=JobResponse, dependencies=[Depends(verify_agent_token)])
async def create_job(job_data: JobCreate, db: Session = Depends(get_db_session)):
    """
    Create a new benchmark job.
    Requires X-Agent-Token.
    """
    # Check if machine exists
    machine = db.query(Machine).filter(Machine.id == job_data.machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    # For now, we just create the job
    new_job = BenchmarkJob(
        machine_id=job_data.machine_id,
        benchmark=job_data.benchmark,
        status="PENDING",
        started_at=datetime.utcnow()
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return new_job

@router.get("/", response_model=List[JobResponse])
async def list_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session)):
    """
    List all benchmark jobs.
    """
    jobs = db.query(BenchmarkJob).offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db_session)):
    """
    Get details of a specific job.
    """
    job = db.query(BenchmarkJob).filter(BenchmarkJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/abort", dependencies=[Depends(verify_agent_token)])
async def abort_job(job_id: int, db: Session = Depends(get_db_session)):
    """
    Abort an existing job.
    Requires X-Agent-Token.
    """
    job = db.query(BenchmarkJob).filter(BenchmarkJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in ["COMPLETED", "FAILED", "ABORTED"]:
        raise HTTPException(status_code=400, detail=f"Cannot abort job in status {job.status}")
    
    job.status = "ABORTED"
    job.finished_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Job {job_id} has been marked as aborted."}
