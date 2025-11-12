# app/api/v1/hr/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

    # app/api/v1/hr/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

# ------------------- JOB (existing) -------------------
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
    status: Optional[str] = Field('open', pattern="^(open|on_hold|closed)$")
    approved_by: Optional[int] = None
    approved_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    job_id: int
    created_by: int
    title: str
    job_code: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    jd: Optional[str] = None
    key_skills: Optional[str] = None
    additional_skills: Optional[str] = None
    openings: Optional[int] = 1
    posted_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    status: Optional[str] = "open"
    approved_by: Optional[int] = None
    approved_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# ------------------- JOB REQUEST (updated) -------------------
class JobRequestCreate(BaseModel):
    manager_name: str = Field(..., description="Full name or username of the manager")
    JobTitle: str = Field(..., max_length=100)
    JobDescription: str
    MinExperienceYears: int = Field(..., ge=0)
    MaxExperienceYears: Optional[int] = None
    KeySkills: Optional[str] = Field(None, max_length=500)
    AdditionalSkills: Optional[str] = Field(None, max_length=500)
    TotalVacancy: int = Field(..., gt=0)
    management_approval: bool = Field(False, description="True = YES, False = NO")

    @validator("MaxExperienceYears")
    def check_max_ge_min(cls, v, values):
        min_exp = values.get("MinExperienceYears")
        if v is not None and min_exp is not None and v < min_exp:
            raise ValueError("MaxExperienceYears must be >= MinExperienceYears")
        return v


class JobRequestResponse(BaseModel):
    JD_ID: int
    manager_id: int
    JobTitle: str
    JobDescription: str
    MinExperienceYears: int
    MaxExperienceYears: Optional[int]
    KeySkills: Optional[str]
    AdditionalSkills: Optional[str]
    TotalVacancy: int
    management_approval: bool

    class Config:
        from_attributes = True  # Replaces orm_mode in Pydantic v2


class JobRequestUpdate(BaseModel):
    # All fields optional for updates (except manager lookup handled by name if provided)
    manager_name: Optional[str] = Field(None, description="Full name or username of the manager")
    JobTitle: Optional[str] = Field(None, max_length=100)
    JobDescription: Optional[str] = None
    MinExperienceYears: Optional[int] = Field(None, ge=0)
    MaxExperienceYears: Optional[int] = None
    KeySkills: Optional[str] = Field(None, max_length=500)
    AdditionalSkills: Optional[str] = Field(None, max_length=500)
    TotalVacancy: Optional[int] = Field(None, gt=0)
    management_approval: Optional[bool] = None

    @validator("MaxExperienceYears")
    def check_max_ge_min(cls, v, values):
        min_exp = values.get("MinExperienceYears")
        if v is not None and min_exp is not None and v < min_exp:
            raise ValueError("MaxExperienceYears must be >= MinExperienceYears")
        return v
    



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
    status: Optional[str] = Field('open', pattern="^(open|on_hold|closed)$")
    approved_by: Optional[int] = None
    approved_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    job_id: int
    created_by: int
    title: str
    job_code: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    jd: Optional[str] = None
    key_skills: Optional[str] = None
    additional_skills: Optional[str] = None
    openings: Optional[int] = 1
    posted_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    status: Optional[str] = "open"
    approved_by: Optional[int] = None
    approved_date: Optional[datetime] = None

    class Config:
        from_attributes = True

# Job Request models
class JobRequestCreate(BaseModel):
    manager_name: str = Field(..., description="Full name or username of the manager")
    JobTitle: str = Field(..., max_length=100)
    JobDescription: str
    MinExperienceYears: int = Field(..., ge=0)
    MaxExperienceYears: Optional[int] = None
    KeySkills: Optional[str] = Field(None, max_length=500)
    AdditionalSkills: Optional[str] = Field(None, max_length=500)
    TotalVacancy: int = Field(..., gt=0)
    management_approval: bool = Field(False, description="True = YES, False = NO")

    @validator("MaxExperienceYears")
    def check_max_ge_min(cls, v, values):
        min_exp = values.get("MinExperienceYears")
        if v is not None and min_exp is not None and v < min_exp:
            raise ValueError("MaxExperienceYears must be >= MinExperienceYears")
        return v

class JobRequestResponse(BaseModel):
    JD_ID: int
    manager_id: int
    JobTitle: str
    JobDescription: str
    MinExperienceYears: int
    MaxExperienceYears: Optional[int]
    KeySkills: Optional[str]
    AdditionalSkills: Optional[str]
    TotalVacancy: int
    management_approval: bool

    class Config:
        from_attributes = True

class JobRequestUpdate(BaseModel):
    manager_name: Optional[str] = Field(None, description="Full name or username of the manager")
    JobTitle: Optional[str] = Field(None, max_length=100)
    JobDescription: Optional[str] = None
    MinExperienceYears: Optional[int] = Field(None, ge=0)
    MaxExperienceYears: Optional[int] = None
    KeySkills: Optional[str] = Field(None, max_length=500)
    AdditionalSkills: Optional[str] = Field(None, max_length=500)
    TotalVacancy: Optional[int] = Field(None, gt=0)
    management_approval: Optional[bool] = None

    @validator("MaxExperienceYears")
    def check_max_ge_min(cls, v, values):
        min_exp = values.get("MinExperienceYears")
        if v is not None and min_exp is not None and v < min_exp:
            raise ValueError("MaxExperienceYears must be >= MinExperienceYears")
        return v

