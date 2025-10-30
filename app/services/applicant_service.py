# app/services/applicant_service.py
import shutil
import os
from sqlalchemy.orm import Session
from datetime import datetime

UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_resume(file, applicant_id: int):
    file_path = os.path.join(UPLOAD_DIR, f"{applicant_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path

def create_applicant(db: Session, applicant_data: dict, resume_file):
    # Insert into applicants table
    query = """
        INSERT INTO applicants (
            first_name, last_name, email, phone, linkedin_url,
            experience_years, education, current_company, current_role,
            expected_ctc, notice_period_days, skills, location, resume_url, created_at, updated_at
        ) VALUES (
            :first_name, :last_name, :email, :phone, :linkedin_url,
            :experience_years, :education, :current_company, :current_role,
            :expected_ctc, :notice_period_days, :skills, :location, :resume_url, :created_at, :updated_at
        );
        SELECT SCOPE_IDENTITY() AS applicant_id;
    """
    now = datetime.now()
    params = {**applicant_data, "resume_url": "", "created_at": now, "updated_at": now}
    result = db.execute(query, params)
    applicant_id = int(result.fetchone()[0])

    # Save resume PDF
    if resume_file:
        file_path = save_resume(resume_file, applicant_id)
        db.execute("UPDATE applicants SET resume_url = :resume_url WHERE applicant_id = :applicant_id",
                   {"resume_url": file_path, "applicant_id": applicant_id})

    db.commit()
    return applicant_id
