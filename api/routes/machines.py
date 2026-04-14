# ~/benchmaster/api/routes/machines.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from db.models import get_engine, get_session, Machine
from api.dependencies import verify_agent_token

router = APIRouter()

# --- Pydantic Models ---

class MachineBase(BaseModel):
    hostname: str
    ip: str
    cpu: Optional[str] = None
    gpu: Optional[str] = None
    ram: Optional[str] = None
    os: Optional[str] = None

class MachineCreate(MachineBase):
    pass

class MachineResponse(MachineBase):
    id: int
    first_seen: datetime
    last_heartbeat: datetime

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

@router.post("/", response_model=MachineResponse, dependencies=[Depends(verify_agent_token)])
async def register_machine(machine_data: MachineCreate, db: Session = Depends(get_db_session)):
    """
    Register a new machine in the fleet.
    Requires X-Agent-Token.
    """
    existing = db.query(Machine).filter(Machine.hostname == machine_data.hostname).first()
    if existing:
        # Update existing machine info (heartbeat/specs)
        for key, value in machine_data.dict().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    new_machine = Machine(**machine_data.dict())
    db.add(new_machine)
    db.commit()
    db.refresh(new_machine)
    return new_machine

@router.get("/", response_model=List[MachineResponse])
async def list_machines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session)):
    """
    List all machines in the fleet.
    """
    machines = db.query(Machine).offset(skip).limit(limit).all()
    return machines

@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(machine_id: int, db: Session = Depends(get_db_session)):
    """
    Get details for a specific machine.
    """
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return machine
