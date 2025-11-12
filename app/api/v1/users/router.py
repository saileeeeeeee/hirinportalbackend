# app/api/v1/applicants/router.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.connection import get_db
from app.services.applicant_service import create_applicant, get_all_applicants
from app.api.v1.applicants.schemas import ApplicantCreate  # optional, keep if used


# ----------------------------------------------------------------------
# DO NOT set prefix here – it's added in main.py as "/api/v1/applicants"
# ----------------------------------------------------------------------
router = APIRouter()   # ← This is imported as `applicants_router` in main.py


@router.post("/", status_code=201)
async def add_applicant(
    # Required fields
    job_id: int = Form(...),
    source: str = Form(...),
    application_status: str = Form(...),

    # Personal info
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),

    # Professional info
    experience_years: Optional[float] = Form(None),
    education: Optional[str] = Form(None),
    current_company: Optional[str] = Form(None),
    current_role: Optional[str] = Form(None),
    expected_ctc: Optional[float] = Form(None),
    notice_period_days: Optional[int] = Form(None),
    skills: Optional[str] = Form(None),
    location: Optional[str] = Form(None),

    # File
    resume: UploadFile = File(...),

    # DB
    db: Session = Depends(get_db),
):
    """
    Create a new applicant with resume upload.
    All fields are form-data (multipart/form-data).
    """
    applicant_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "linkedin_url": linkedin_url,
        "experience_years": experience_years,
        "education": education,
        "current_company": current_company,
        "current_role": current_role,
        "expected_ctc": expected_ctc,
        "notice_period_days": notice_period_days,
        "skills": skills,
        "location": location,
        "job_id": job_id,
        "source": source,
        "application_status": application_status,
    }

    try:
        applicant_id = create_applicant(db, applicant_data, resume)
        return {
            "message": "Applicant created successfully",
            "applicant_id": applicant_id
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/applicants", response_model=List[dict])
async def get_applicants(db: Session = Depends(get_db)):
    """
    Retrieve all applicants.
    """
    try:
        applicants = get_all_applicants(db)
        if not applicants:
            raise HTTPException(status_code=404, detail="No applicants found")
        return applicants
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching applicants: {str(exc)}"
        ) from exc