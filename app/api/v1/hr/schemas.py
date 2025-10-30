# app/api/v1/hr/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class JobCreate(BaseModel):
    created_by: int
    title: str
    job_code: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = Field(
        None, pattern="^(Full-time|Part-time|Contract|Internship)$"
    )
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    jd: Optional[str] = None
    key_skills: Optional[str] = None
    additional_skills: Optional[str] = None
    openings: Optional[int] = 1
    posted_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    status: Optional[str] = Field(
        'open', pattern="^(open|on_hold|closed)$"
    )
    approved_by: Optional[int] = None
    approved_date: Optional[datetime] = None
