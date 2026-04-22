# ~/benchmaster/api/routes/jobs.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from db.models import get_engine, get_session, BenchmarkJob, Machine, Result
from pydantic import BaseModel
from api.dependencies import verify_agent_token
from api.mqtt_manager import mqtt_manager

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
    Create a new benchmark job and notify the machine via MQTT.
    """
    # Check if machine exists
    machine = db.query(Machine).filter(Machine.id == job_data.machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Create the job record
    new_job = BenchmarkJob(
        machine_id=job_data.machine_id,
        benchmark=job_data.benchmark,
        status="PENDING",
        started_at=datetime.now(timezone.utc)
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # --- MQTT Trigger ---
    # Push the task to the specific machine's topic
    mqtt_manager.publish_task(new_job.machine_id, {
        "id": new_job.id,
        "benchmark": new_job.benchmark,
        "action": "START"
    })
    
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
    Abort an existing job and notify the machine via MQTT.
    """
    job = db.query(BenchmarkJob).filter(BenchmarkJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in ["COMPLETED", "FAILED", "ABORTED"]:
        raise HTTPException(status_code=400, detail=f"Cannot abort job in status {job.status}")
    
    job.status = "ABORTED"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    
    # --- MQTT Trigger ---
    # Push the abort command to the specific machine's topic
    mqtt_manager.publish_task(job.machine_id, {
        "id": job.id,
        "action": "ABORT"
    })
    
    return {"message": f"Job {job_id} has been marked as aborted."}
