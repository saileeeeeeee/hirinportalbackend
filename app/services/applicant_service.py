import shutil
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from .aishortlist import evaluate_resume_match  # Ensure this import is correct
from typing import List
from fastapi import HTTPException, Depends
from app.db.connection import get_db

# Setup logging configuration
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all levels of logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]  # Logs will be printed to console
)


UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_resume(upload_file: UploadFile, applicant_id: int) -> str:
    """Save resume with proper applicant_id and year-month folder."""
    try:
        if not upload_file.filename:
            raise ValueError("No filename")

        year_month = datetime.now().strftime("%Y-%m")
        directory = os.path.join(UPLOAD_DIR, year_month)
        os.makedirs(directory, exist_ok=True)

        filename = f"{applicant_id}_{upload_file.filename}"
        file_path = os.path.join(directory, filename)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)

        logging.info(f"Resume saved: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Save resume failed: {e}")
        raise


def create_applicant(db: Session, applicant_data: dict, resume_file, job_id: int, source: str, application_status: str, assigned_hr: str = None, assigned_manager: str = None, comments: str = None):
    """Function to create an applicant, save their resume, and create an application entry in the applications table."""
    try:
        # Start a transaction
        with db.begin():  # This ensures automatic commit or rollback
            # Generate current timestamp for created_at and updated_at
            now = datetime.now()
            params = {**applicant_data, "resume_url": None, "created_at": now, "updated_at": now}
            
            # Log applicant data being inserted
            logging.info(f"Inserting applicant data: {applicant_data}")

            # Insert applicant data into the applicants table
            db.execute(text(""" 
                INSERT INTO applicants (
                    first_name, last_name, email, phone, linkedin_url,
                    experience_years, education, current_company, current_role,
                    expected_ctc, notice_period_days, skills, location, resume_url, created_at, updated_at
                ) VALUES (
                    :first_name, :last_name, :email, :phone, :linkedin_url,
                    :experience_years, :education, :current_company, :current_role,
                    :expected_ctc, :notice_period_days, :skills, :location, :resume_url, :created_at, :updated_at
                );
            """), params)

            # Fetch the last inserted applicant_id using SCOPE_IDENTITY()
            logging.info("Fetching applicant_id of the newly inserted applicant.")
            result = db.execute(text("SELECT SCOPE_IDENTITY() AS applicant_id;"))
            applicant_id = result.fetchone()[0]
            logging.info(f"Applicant ID: {applicant_id} retrieved successfully.")

            # Handle resume file if provided
            if resume_file:
                logging.info(f"Resume file found for applicant {applicant_id}, saving the file.")
                file_path = save_resume(resume_file, applicant_id)
                logging.info(f"Resume file path: {file_path}")
                
                # Update the resume URL in the database for the applicant
                logging.info(f"Updating applicant record with resume URL: {file_path}")
                db.execute(text("UPDATE applicants SET resume_url = :resume_url WHERE applicant_id = :applicant_id"),
                           {"resume_url": file_path, "applicant_id": applicant_id})

            # Insert into applications table with created_at and updated_at
            application_params = {
                "applicant_id": applicant_id,
                "job_id": job_id,
                "application_status": application_status,
                "source": source,
                "assigned_hr": assigned_hr,
                "assigned_manager": assigned_manager,
                "comments": comments,
                "created_at": now,  # Set created_at to current timestamp
                "updated_at": now   # Set updated_at to current timestamp
            }
            
            logging.info(f"Inserting application for applicant {applicant_id} and job {job_id}.")
            db.execute(text(""" 
                INSERT INTO applications (
                    applicant_id, job_id, application_status, source, assigned_hr,
                    assigned_manager, comments, updated_at
                ) VALUES (
                    :applicant_id, :job_id, :application_status, :source, :assigned_hr,
                    :assigned_manager, :comments,:updated_at
                );
            """), application_params)

            logging.info(f"Application created for applicant {applicant_id} and job {job_id}.")

            # Trigger resume evaluation (passing relevant params)
            evaluation_result = trigger_evaluate_resume_match(
                resume_pdf_path=file_path,
                jd_text=get_jd(job_id, db),
                high_priority_keywords=get_high_priority_keywords(job_id, db),
                normal_keywords=get_normal_keywords(job_id, db),
                job_id=job_id,
                applicant_id=applicant_id,
                source=source,
                application_status=application_status,
                assigned_hr=assigned_hr,
                assigned_manager=assigned_manager,
                comments=comments,
                db=db
            )

            logging.info(f"Evaluation result: {evaluation_result}")
            return {
                "applicant_id": applicant_id,
                "resume_url": file_path,
                "evaluation_result": evaluation_result,
                **{k: v for k, v in applicant_data.items() if k != 'resume_url'}
            }

    except Exception as e:
        # Rollback in case of any error
        logging.error(f"Error while creating applicant and application: {e}")
        db.rollback()
        logging.debug("Transaction rolled back.")
        raise HTTPException(status_code=500, detail=f"Failed to create applicant and application: {str(e)}")


# Function to evaluate resume match (triggered after creating applicant)
def trigger_evaluate_resume_match(
    resume_pdf_path, jd_text, high_priority_keywords, normal_keywords, 
    job_id, applicant_id, source, application_status, 
    assigned_hr=None, assigned_manager=None, comments=None, db: Session = Depends(get_db)
):
    """Evaluates a resume match against a job description and stores the results in the database."""
    try:
        # Assume `evaluate_resume_match` is defined earlier in the system as provided by you earlier.
        result = evaluate_resume_match(
            resume_pdf_path=resume_pdf_path,
            jd_text=jd_text,
            high_priority_keywords=high_priority_keywords,
            normal_keywords=normal_keywords,
            job_id=job_id,
            applicant_id=applicant_id,
            source=source,
            application_status=application_status,
            assigned_hr=assigned_hr,
            assigned_manager=assigned_manager,
            comments=comments,
            db=db
        )
        return result
    except Exception as e:
        logging.error(f"Failed to evaluate resume match: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during resume evaluation: {str(e)}")


# Example of helper functions to retrieve job description and keywords
def get_jd(job_id: int, db: Session) -> str:
    """Fetch job description from database for the given job_id."""
    query = text("SELECT jd FROM jobs WHERE job_id = :job_id")
    result = db.execute(query, {"job_id": job_id}).fetchone()
    return result[0] if result else ""


def get_high_priority_keywords(job_id: int, db: Session) -> set:
    """Fetch high priority keywords for the job."""
    query = text("SELECT key_skills FROM jobs  WHERE job_id = :job_id ")
    result = db.execute(query, {"job_id": job_id}).fetchall()
    return {row[0] for row in result}


def get_normal_keywords(job_id: int, db: Session) -> set:
    """Fetch normal keywords for the job."""
    query = text("SELECT additional_skills FROM jobs  WHERE job_id = :job_id ")
    result = db.execute(query, {"job_id": job_id}).fetchall()
    return {row[0] for row in result}






def get_all_applicants(db: Session) -> List[dict]:
    """
    Fetch ALL applications + applicant data (even if applicant missing)
    Uses LEFT JOIN to show application even if applicant deleted
    """
    try:
        query = text("""
            SELECT 
                app.application_id,
                app.job_id,
                app.applicant_id,
                app.applied_date,
                app.source,
                app.skills_matching_score,
                app.jd_matching_score,
                app.resume_overall_score,
                app.application_status,
                app.assigned_hr,
                app.assigned_manager,
                app.comments,
                app.updated_at AS app_updated_at,
                
                a.applicant_id AS a_applicant_id,
                a.first_name,
                a.last_name,
                a.email,
                a.phone,
                a.linkedin_url,
                a.resume_url,
                a.experience_years,
                a.education,
                a.current_company,
                a.current_role,
                a.expected_ctc,
                a.notice_period_days,
                a.skills,
                a.location,
                a.created_at AS a_created_at,
                a.updated_at AS a_updated_at
            FROM applications app
            LEFT JOIN applicants a ON app.application_id = a.applicant_id
            ORDER BY app.applied_date DESC
        """)

        result = db.execute(query).mappings().fetchall()
        if not result:
            return []

        applicants = []
        for row in result:
            applicants.append({
                # Application
                "application_id": row.get("application_id"),
                "job_id": row.get("job_id"),
                "applicant_id": row.get("applicant_id"),
                "applied_date": row.get("applied_date"),
                "source": row.get("source"),
                "skills_matching_score": row.get("skills_matching_score"),
                "jd_matching_score": row.get("jd_matching_score"),
                "resume_overall_score": row.get("resume_overall_score"),
                "application_status": row.get("application_status") or "pending",
                "assigned_hr": row.get("assigned_hr"),
                "assigned_manager": row.get("assigned_manager"),
                "comments": row.get("comments"),
                "updated_at": row.get("app_updated_at"),

                # Applicant (may be null)
                "first_name": row.get("first_name") or "Unknown",
                "last_name": row.get("last_name") or "Applicant",
                "email": row.get("email") or "N/A",
                "phone": row.get("phone"),
                "linkedin_url": row.get("linkedin_url"),
                "resume_url": row.get("resume_url"),
                "experience_years": row.get("experience_years", 0),
                "education": row.get("education"),
                "current_company": row.get("current_company"),
                "current_role": row.get("current_role"),
                "expected_ctc": row.get("expected_ctc", 0.0),
                "notice_period_days": row.get("notice_period_days", 0),
                "skills": row.get("skills"),
                "location": row.get("location"),
                "created_at": row.get("a_created_at"),
                "applicant_updated_at": row.get("a_updated_at"),
            })

        return applicants

    except Exception as e:
        logging.error(f"Database error in get_all_applicants: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch applicants.")
    




    