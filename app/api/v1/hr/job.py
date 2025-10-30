# app/api/v1/hr/job.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.connection import get_db
from app.api.v1.hr.schemas import JobCreate
from app.services.job_service import *

router = APIRouter(prefix="/hr/jobs", tags=["HR Jobs"])

@router.post("/", status_code=201)
def add_job(job: JobCreate, db: Session = Depends(get_db)):
    try:
        job_id = create_job(db, job)
        return {"message": "Job created successfully", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/", status_code=200)
def list_active_jobs(db: Session = Depends(get_db)):
    jobs = get_active_jobs(db)
    return {"active_jobs": jobs}


