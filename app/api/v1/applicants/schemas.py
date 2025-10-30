# app/api/v1/applicants/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class ApplicantCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str]
    linkedin_url: Optional[str]
    experience_years: Optional[float]
    education: Optional[str]
    current_company: Optional[str]
    current_role: Optional[str]
    expected_ctc: Optional[float]
    notice_period_days: Optional[int]
    skills: Optional[str]
    location: Optional[str]
