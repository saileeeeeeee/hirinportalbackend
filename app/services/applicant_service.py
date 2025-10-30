import shutil
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_resume(file, applicant_id: int):
    file_path = os.path.join(UPLOAD_DIR, f"{applicant_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path

def create_applicant(db: Session, applicant_data: dict, resume_file):
    try:
        # Prepare insert data
        now = datetime.now()
        params = {**applicant_data, "resume_url": "", "created_at": now, "updated_at": now}
        
        # Insert new applicant data (Without the SELECT for ID)
        insert_query = text("""
            INSERT INTO applicants (
                first_name, last_name, email, phone, linkedin_url,
                experience_years, education, current_company, current_role,
                expected_ctc, notice_period_days, skills, location, resume_url, created_at, updated_at
            ) VALUES (
                :first_name, :last_name, :email, :phone, :linkedin_url,
                :experience_years, :education, :current_company, :current_role,
                :expected_ctc, :notice_period_days, :skills, :location, :resume_url, :created_at, :updated_at
            );
        """)
        db.execute(insert_query, params)

        # Now fetch the last inserted applicant_id using SCOPE_IDENTITY()
        result = db.execute(text("SELECT SCOPE_IDENTITY() AS applicant_id;"))
        applicant_id = result.fetchone()[0]
        print(f"Applicant ID: {applicant_id}")

        # Save resume if a file is provided
        if resume_file:
            file_path = save_resume(resume_file, applicant_id)
            # Update the resume URL with the file path
            db.execute(text("UPDATE applicants SET resume_url = :resume_url WHERE applicant_id = :applicant_id"),
                       {"resume_url": file_path, "applicant_id": applicant_id})

        # Commit the transaction
        db.commit()
        return applicant_id

    except Exception as e:
        # Rollback in case of any error
        db.rollback()
        print(f"Error while creating applicant: {e}")
        raise  # Reraise the exception to handle it higher up
