from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any

class ApplicantCreate(BaseModel):
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    email: EmailStr = Field(..., description="Valid email")
    phone: Optional[str] = Field(
        None,
        pattern=r"^\+?\d{10,15}$",  # pydantic v2 uses 'pattern' instead of 'regex'
        description="Phone: 10–15 digits, optional + prefix"
    )
    linkedin_url: Optional[str] = Field(None, description="Full LinkedIn URL")
    experience_years: Optional[float] = Field(None, ge=0, description="Years of experience")
    education: Optional[str] = Field(None, description="Highest degree")
    current_company: Optional[str] = Field(None, description="Current company")
    current_role: Optional[str] = Field(None, description="Current role")
    expected_ctc: Optional[float] = Field(None, ge=0, description="Expected CTC in LPA")
    notice_period_days: Optional[int] = Field(None, ge=0, description="Notice period in days")
    skills: Optional[str] = Field(None, description="Comma-separated skills")
    location: Optional[str] = Field(None, description="Current location")


class BulkApplicantCreate(BaseModel):
    job_id: int = Field(..., gt=0, description="Job ID (integer > 0)")
    source: str = Field(..., min_length=1, max_length=100, description="Source e.g. LinkedIn")
    application_status: str = Field("pending", description="Default: pending")
    expected_ctc: Optional[float] = Field(None, ge=0)
    notice_period_days: Optional[int] = Field(None, ge=0)
    assigned_hr: Optional[int] = Field(None, gt=0, description="HR User ID (integer)")
    assigned_manager: Optional[int] = Field(None, gt=0, description="Manager User ID (integer)")
    comments: Optional[str] = Field(None, max_length=1000)

    class Config:
        # Example in JSON schema
        json_schema_extra = {
            "example": {
                "job_id": 7,
                "source": "LinkedIn",
                "assigned_hr": 3,
                "assigned_manager": 5,
                "comments": "Strong in Python & AWS"
            }
        }


class ApplicantResponse(BaseModel):
    applicant_id: int
    first_name: str
    last_name: str
    email: EmailStr
    resume_url: str
    evaluation_result: Dict[str, Any] = Field(default_factory=dict)

    # Pydantic v2: allow model creation from ORM-style attributes
    model_config = ConfigDict(from_attributes=True)


class BulkUploadSummary(BaseModel):
    message: str
    total: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
    errors: List[str]
