# app/api/v1/hr/job.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.connection import get_db
from app.api.v1.hr.schemas import JobCreate, JobResponse
from app.services.job_service import (
    create_job,
    get_active_jobs,
    get_job_by_id,
)


# ----------------------------------------------------------------------
# Router imported in main.py as `hr_job_router`
# Prefix "/api/v1/hr/jobs" is added in main.py
# ----------------------------------------------------------------------
router = APIRouter(tags=["HR Jobs"])


@router.post("/", status_code=201, response_model=Dict[str, Any])
def add_job(job: JobCreate, db: Session = Depends(get_db)):
    """
    Create a new job posting.
    """
    try:
        result = create_job(db, job)
        return {"message": "Job created successfully", "data": result}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to create job: {str(exc)}") from exc


# app/api/v1/hr/job.py

@router.get("/", response_model=dict)
def list_active_jobs(db: Session = Depends(get_db)):
    try:
        jobs = get_active_jobs(db)
        return {"active_jobs": jobs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{job_id}", response_model=JobResponse)
def read_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get a single job by ID.
    Used by frontend: http://localhost:8000/api/v1/hr/jobs/2
    """
    try:
        job = get_job_by_id(db, job_id)
        return job
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(exc)}"
        ) from exc