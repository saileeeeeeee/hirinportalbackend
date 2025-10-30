# app/api/v1/applicants/router.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.db.connection import get_db
from app.services.applicant_service import create_applicant
from app.api.v1.applicants.schemas import ApplicantCreate

router = APIRouter(prefix="/applicants", tags=["Applicants"])

@router.post("/", status_code=201)
async def add_applicant(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    experience_years: Optional[float] = Form(None),
    education: Optional[str] = Form(None),
    current_company: Optional[str] = Form(None),
    current_role: Optional[str] = Form(None),
    expected_ctc: Optional[float] = Form(None),
    notice_period_days: Optional[int] = Form(None),
    skills: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
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
        "location": location
    }

    try:
        applicant_id = create_applicant(db, applicant_data, resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Applicant created successfully", "applicant_id": applicant_id}
