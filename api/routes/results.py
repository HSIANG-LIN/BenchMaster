# ~/benchmaster/api/routes/results.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

from db.models import get_engine, get_session, Result, BenchmarkJob, Machine
from api.dependencies import verify_agent_token

router = APIRouter()

# --- Pydantic Models ---

class ResultCreate(BaseModel):
    job_id: int
    machine_id: int
    benchmark: str
    scores_json: Dict[str, float]
    system_snapshot_json: Dict[str, Any]
    tags: Optional[str] = None
    pass_fail: str

class ResultResponse(BaseModel):
    id: int
    job_id: int
    machine_id: int
    benchmark: str
    timestamp: datetime
    scores_json: Dict[str, float]
    system_snapshot_json: Dict[str, Any]
    tags: Optional[str]
    pass_fail: str

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

@router.post("/", response_model=ResultResponse, dependencies=[Depends(verify_agent_token)])
async def create_result(result_data: ResultCreate, db: Session = Depends(get_db_session)):
    """
    Upload a new benchmark result.
    Requires X-Agent-Token.
    """
    # 1. Verify Job exists and belongs to this machine
    job = db.query(BenchmarkJob).filter(
        BenchmarkJob.id == result_data.job_id,
        BenchmarkJob.machine_id == result_data.machine_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or machine mismatch")

    # 2. Create Result
    new_result = Result(
        job_id=result_data.job_id,
        machine_id=result_data.machine_id,
        benchmark=result_data.benchmark,
        scores_json=result_data.scores_json,
        system_snapshot_json=result_data.system_snapshot_json,
        tags=result_data.tags,
        pass_fail=result_data.pass_fail,
        timestamp=datetime.utcnow()
    )
    
    db.add(new_result)
    db.commit()
    db.refresh(new_result)
    
    # 3. Update Job status to COMPLETED
    job.status = "COMPLETED"
    job.finished_at = datetime.utcnow()
    db.commit()
    
    return new_result

@router.get("/", response_model=List[ResultResponse])
async def list_results(benchmark: str = None, machine_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session)):
    """
    List all benchmark results, with optional filtering.
    """
    query = db.query(Result)
    
    if benchmark:
        query = query.filter(Result.benchmark == benchmark)
    if machine_id:
        query = query.filter(Result.machine_id == machine_id)
        
    results = query.offset(skip).limit(limit).all()
    return results

@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(result_id: int, db: Session = Depends(get_db_session)):
    """
    Get a specific result by ID.
    """
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return result
