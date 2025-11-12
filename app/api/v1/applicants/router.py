from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.db.connection import get_db
from app.services.applicant_service import create_applicant, get_all_applicants
from app.services.bulk_applicant_service import create_applicant_from_pdf
from app.api.v1.applicants.schemas import (
    ApplicantCreate, BulkApplicantCreate, BulkUploadSummary, ApplicantResponse
)

router = APIRouter()


# @router.post("/applicants", status_code=201, response_model=ApplicantResponse)
# async def add_applicant(
#     # Required
#     job_id: int = Form(...),
#     source: str = Form(...),
#     application_status: str = Form("pending"),
#     first_name: str = Form(...),
#     last_name: str = Form(...),
#     email: str = Form(...),
#     # Optional
#     phone: Optional[str] = Form(None),
#     linkedin_url: Optional[str] = Form(None),
#     experience_years: Optional[float] = Form(None),
#     education: Optional[str] = Form(None),
#     current_company: Optional[str] = Form(None),
#     current_role: Optional[str] = Form(None),
#     expected_ctc: Optional[float] = Form(None),
#     notice_period_days: Optional[int] = Form(None),
#     skills: Optional[str] = Form(None),
#     location: Optional[str] = Form(None),
#     resume: UploadFile = File(...),
#     db: Session = Depends(get_db),
# ):
#     applicant_data = {
#         "first_name": first_name,
#         "last_name": last_name,
#         "email": email,
#         "phone": phone,
#         "linkedin_url": linkedin_url,
#         "experience_years": experience_years,
#         "education": education,
#         "current_company": current_company,
#         "current_role": current_role,
#         "expected_ctc": expected_ctc,
#         "notice_period_days": notice_period_days,
#         "skills": skills,
#         "location": location,
#     }
#     try:
#         applicant_id = create_applicant(
#             db=db,
#             applicant_data=applicant_data,
#             resume=resume,
#             job_id=job_id,
#             source=source,
#             application_status=application_status,
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")
#     return ApplicantResponse(
#         applicant_id=applicant_id,
#         first_name=first_name,
#         last_name=last_name,
#         email=email,
#         resume_url=f"uploads/resumes/{applicant_id}_{resume.filename}",
#         evaluation_result={}
#     )


@router.get("/applicants", response_model=List[dict])
async def get_applicants(db: Session = Depends(get_db)):
    applicants = get_all_applicants(db)
    if not applicants:
        raise HTTPException(status_code=404, detail="No applicants found")
    return applicants


@router.post(
    "/bulk-applicants",
    status_code=202,
    response_model=BulkUploadSummary,
    summary="Bulk upload resumes",
    description="assigned_hr & assigned_manager must be integers"
)
async def bulk_upload_applicants(
    payload: BulkApplicantCreate = Depends(),
    resumes: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if not resumes:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results: List[Dict] = []

    for resume in resumes:
        # default per-file result template
        file_result = {
            "filename": resume.filename or "unknown",
            "applicant_id": None,
            "email": None,
            "name": None,
            "status": "failed",
            "status_code": None,
            "error": None
        }

        if not resume.filename or not resume.filename.lower().endswith(".pdf"):
            file_result["error"] = "Invalid file type (only PDFs allowed)"
            file_result["status_code"] = 400
            results.append(file_result)
            continue

        try:
            result = create_applicant_from_pdf(
                db=db,
                pdf_file=resume,
                job_id=payload.job_id,
                source=payload.source,
                expected_ctc=payload.expected_ctc,
                notice_period_days=payload.notice_period_days,
                application_status=payload.application_status,
                assigned_hr=payload.assigned_hr,
                assigned_manager=payload.assigned_manager,
                comments=payload.comments,
            )
            parsed = result.get("parsed", {})
            name = f"{parsed.get('first_name','')} {parsed.get('last_name','')}".strip() or "Unknown"

            file_result.update({
                "applicant_id": result.get("applicant_id"),
                "email": parsed.get("email"),
                "name": name,
                "status": "success",
                "status_code": 201,
                "error": None
            })
        except HTTPException as he:
            # we got an HTTPException from inside create_applicant_from_pdf (good to propagate its detail)
            file_result["error"] = he.detail if isinstance(he.detail, str) else str(he.detail)
            file_result["status_code"] = he.status_code or 500
            file_result["status"] = "failed"
        except Exception as e:
            # generic exception
            logging.exception(f"Unexpected error processing {resume.filename}: {e}")
            file_result["error"] = str(e)
            file_result["status_code"] = 500
            file_result["status"] = "failed"
        finally:
            # Always append a per-file result
            results.append(file_result)

    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    return BulkUploadSummary(
        message="Bulk upload completed",
        total=len(resumes),
        successful=successful,
        failed=failed,
        results=results,
        errors=[r["error"] for r in results if r["error"]]
    )
