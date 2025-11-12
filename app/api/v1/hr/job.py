# app/api/v1/hr/job.py

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.db.connection import get_db
from app.api.v1.hr.schemas import (
    JobCreate,
    JobResponse,
    JobRequestCreate,
    JobRequestResponse,
    JobRequestUpdate
)
from app.services.job_service import (
    # --- Jobs Table Functions ---
    create_job,
    get_active_jobs,
    get_job_by_id,

    # --- Job_Request Table Functions ---
    create_job_request,
    get_job_request_by_id,
    list_job_requests,
    update_job_request_approval,
    delete_job_request,
    update_job_request,
)
# ----------------------------------------------------------------------
# Router imported in main.py as `hr_job_router`
# Prefix "/api/v1/hr/jobs" is added in main.py
# ----------------------------------------------------------------------
router = APIRouter(tags=["HR Jobs & Job Requests"])


# ==============================
#      JOB REQUEST ENDPOINTS
# ==============================

@router.post("/request", response_model=JobRequestResponse, status_code=201)
def add_job_request(payload: JobRequestCreate, db: Session = Depends(get_db)):
    """
    Create a new **Job Request** (goes into `Job_Request` table).
    """
    return create_job_request(db, payload)


@router.get("/request/{jd_id}", response_model=JobRequestResponse)
def read_job_request(jd_id: int, db: Session = Depends(get_db)):
    """Fetch a single job request by JD_ID."""
    return get_job_request_by_id(db, jd_id)


@router.get("/request", response_model=List[JobRequestResponse])
def list_all_job_requests(
    approved: Optional[bool] = Query(None, description="Filter by management approval: true/false"),
    db: Session = Depends(get_db),
):
    """
    Return all job requests.
    Use `?approved=true` or `?approved=false` to filter.
    """
    return list_job_requests(db, approved)


@router.patch("/request/{jd_id}/approve", response_model=JobRequestResponse)
def approve_job_request(jd_id: int, approve: bool = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Set management_approval to true/false for JD.
    Body: { "approve": true } or { "approve": false }
    """
    try:
        return update_job_request_approval(db, jd_id, approve)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/request/{jd_id}", status_code=200)
def remove_job_request(jd_id: int, db: Session = Depends(get_db)):
    """Delete a job request."""
    try:
        return delete_job_request(db, jd_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/request/{jd_id}", response_model=JobRequestResponse)
def edit_job_request(jd_id: int, payload: JobRequestUpdate, db: Session = Depends(get_db)):
    """Full/partial update for a job request (fields optional)."""
    try:
        return update_job_request(db, jd_id, payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ==============================
#        JOB POSTING ENDPOINTS
# ==============================

@router.post("/", status_code=201, response_model=Dict[str, Any])
def add_job(job: JobCreate, db: Session = Depends(get_db)):
    """
    Create a new **Job Posting** (goes into `jobs` table).
    """
    try:
        result = create_job(db, job)
        return {"message": "Job created successfully", "data": result}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to create job: {str(exc)}") from exc


@router.get("/", response_model=Dict[str, Any])
def list_active_jobs(db: Session = Depends(get_db)):
    """List all active (open) job postings."""
    try:
        jobs = get_active_jobs(db)
        return {"active_jobs": jobs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{job_id}", response_model=JobResponse)
def read_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get a single job posting by ID.
    Example: GET /api/v1/hr/jobs/2
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
