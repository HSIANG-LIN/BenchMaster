# ~/benchmaster/db/models.py

import os
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, 
    DateTime, JSON, Boolean, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class Machine(Base):
    """
    Stores information about each Windows host agent.
    """
    __tablename__ = 'machines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String(255), unique=True, nullable=False)
    ip = Column(String(45), nullable=False)
    cpu = Column(String(255))
    gpu = Column(String(255))
    ram = Column(String(50))
    os = Column(String(255))
    # Real-time metrics
    cpu_usage_percent = Column(Float, default=0.0)
    memory_used_mb = Column(Float, default=0.0)
    memory_total_mb = Column(Float, default=0.0)
    disk_usage_percent = Column(Float, default=0.0)
    network_rx_mbps = Column(Float, default=0.0)
    network_tx_mbps = Column(Float, default=0.0)
    last_metrics_update = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    # Legacy fields
    first_seen = Column(DateTime, default=get_utc_now)
    last_heartbeat = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    status = Column(String(50), default='ONLINE')
    schedule_cron = Column(String(100), nullable=True) # Cron expression for automated tests

    # Relationships
    jobs = relationship("BenchmarkJob", back_populates="machine", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="machine", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="machine", cascade="all, delete-orphan")

class BenchmarkJob(Base):
    """
    Tracks the lifecycle of a benchmark execution.
    """
    __tablename__ = 'benchmark_jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    benchmark = Column(String(100), nullable=False)
    status = Column(String(50), default='PENDING')  # PENDING, RUNNING, COMPLETED, FAILED, ABORTED
    started_at = Column(DateTime)
    finished_at = Column(DateTime)

    # Relationships
    machine = relationship("Machine", back_populates="jobs")
    result = relationship("Result", back_populates="job", uselist=False, cascade="all, delete-orphan")

class Result(Base):
    """
    Stores the detailed scores and snapshots from a completed benchmark.
    """
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('benchmark_jobs.id'), nullable=False)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    benchmark = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=get_utc_now)
    scores_json = Column(JSON, nullable=False)          # e.g., {"single_core": 1200.5}
    system_snapshot_json = Column(JSON, nullable=False) # e.g., {"cpu": "...", "gpu": "..."}
    tags = Column(String(500))                          # Stored as comma-separated string
    pass_fail = Column(String(10))                      # PASS or FAIL
    threshold_ref = Column(String(100))                 # Reference to the threshold used

    # Relationships
    job = relationship("BenchmarkJob", back_populates="result")
    machine = relationship("Machine", back_populates="results")
    alert = relationship("Alert", back_populates="result", uselist=False)

class Threshold(Base):
    """
    Defines pass/fail criteria for specific benchmark metrics.
    """
    __tablename__ = 'thresholds'

    id = Column(Integer, primary_key=True, autoincrement=True)
    benchmark = Column(String(100), nullable=False)
    metric_key = Column(String(100), nullable=False)
    min_val = Column(Float)
    max_val = Column(Float)
    version = Column(String(50))

class Alert(Base):
    """
    Logs system issues or benchmark anomalies.
    """
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    result_id = Column(Integer, ForeignKey('results.id'), nullable=True)
    alert_type = Column(String(100), nullable=False)  # e.g., "OFFLINE", "LOW_SCORE"
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
    acknowledged = Column(Boolean, default=False)

    # Relationships
    machine = relationship("Machine", back_populates="alerts")
    result = relationship("Alert", back_populates="result", uselist=False)

# --- Database Utilities ---

def get_engine(db_url: str = "sqlite:///~/benchmaster/db/benchmaster.db"):
    """
    Creates and returns a SQLAlchemy engine.
    Expands the tilde (~) in the path if present.
    Ensures correct number of slashes for absolute SQLite paths.
    """
    if db_url.startswith("sqlite:///"):
        path = db_url[10:]  # Remove "sqlite:///"
        expanded_path = os.path.expanduser(path)
        # If path is /home/user/db.sqlite, URL must be sqlite:////home/user/db.sqlite
        return create_engine(f"sqlite:///{expanded_path}")
    
    return create_engine(db_url)

def init_db(engine):
    """
    Initializes the database schema.
    """
    Base.metadata.create_all(engine)

def get_session(engine) -> Session:
    """
    Returns a new SQLAlchemy session.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

if __name__ == '__main__':
    # Quick test to initialize the DB
    engine = get_engine()
    init_db(engine)
    print("Database initialized successfully.")
