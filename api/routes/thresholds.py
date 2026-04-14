# ~/benchmaster/api/routes/thresholds.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from typing import Optional

from db.models import get_engine, get_session, Threshold

router = APIRouter()

# --- Pydantic Models ---

class ThresholdBase(BaseModel):
    benchmark: str
    metric_key: str
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    version: Optional[str] = "1.0"

class ThresholdCreate(ThresholdBase):
    pass

class ThresholdResponse(ThresholdBase):
    id: int

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

@router.post("/", response_model=ThresholdResponse)
async def create_threshold(threshold_data: ThresholdCreate, db: Session = Depends(get_db_session)):
    """
    Create a new threshold.
    """
    new_threshold = Threshold(**threshold_data.dict())
    db.add(new_threshold)
    db.commit()
    db.refresh(new_threshold)
    return new_threshold

@router.get("/", response_model=List[ThresholdResponse])
async def list_thresholds(benchmark: Optional[str] = None, db: Session = Depends(get_db_session)):
    """
    List all thresholds, optionally filtered by benchmark.
    """
    query = db.query(Threshold)
    if benchmark:
        query = query.filter(Threshold.benchmark == benchmark)
    
    thresholds = query.all()
    return thresholds

@router.get("/{threshold_id}", response_model=ThresholdResponse)
async def get_threshold(threshold_id: int, db: Session = Depends(get_db_session)):
    """
    Get a specific threshold.
    """
    threshold = db.query(Threshold).filter(Threshold.id == threshold_id).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    return threshold

@router.put("/{threshold_id}", response_model=ThresholdResponse)
async def update_threshold(threshold_id: int, threshold_data: ThresholdCreate, db: Session = Depends(get_db_session)):
    """
    Update an existing threshold.
    """
    threshold = db.query(Threshold).filter(Threshold.id == threshold_id).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    
    for key, value in threshold_data.dict().items():
        setattr(threshold, key, value)
        
    db.commit()
    db.refresh(threshold)
    return threshold

@router.delete("/{threshold_id}")
async def delete_threshold(threshold_id: int, db: Session = Depends(get_db_session)):
    """
    Delete a threshold.
    """
    threshold = db.query(Threshold).filter(Threshold.id == threshold_id).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    
    db.delete(threshold)
    db.commit()
    return {"message": "Threshold deleted successfully"}
