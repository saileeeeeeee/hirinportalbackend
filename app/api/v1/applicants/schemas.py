from pydantic import BaseModel, EmailStr, constr, condecimal
from typing import Optional

class ApplicantCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    experience_years: Optional[float] = None
    education: Optional[str] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    expected_ctc: Optional[float] = None
    notice_period_days: Optional[int] = None
    skills: Optional[str] = None
    location: Optional[str] = None
    job_id: int  # This will now be part of the schema
    source: str  # This will be part of the schema
    application_status: str  # This will be part of the schema

   

