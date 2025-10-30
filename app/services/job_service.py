# app/services/job_service.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.v1.hr.schemas import JobCreate
from datetime import datetime


def create_job(db: Session, job: JobCreate):
    query = text("""
        INSERT INTO jobs (
            created_by, title, job_code, department, location, employment_type,
            experience_required, salary_range, jd, key_skills, additional_skills,
            openings, posted_date, closing_date, status, approved_by, approved_date
        ) VALUES (
            :created_by, :title, :job_code, :department, :location, :employment_type,
            :experience_required, :salary_range, :jd, :key_skills, :additional_skills,
            :openings, :posted_date, :closing_date, :status, :approved_by, :approved_date
        );
        SELECT SCOPE_IDENTITY() AS job_id;
    """)

    # Default posted_date if not provided
    posted_date = job.posted_date or datetime.now()

    result = db.execute(query, {
        "created_by": job.created_by,
        "title": job.title,
        "job_code": job.job_code,
        "department": job.department,
        "location": job.location,
        "employment_type": job.employment_type,
        "experience_required": job.experience_required,
        "salary_range": job.salary_range,
        "jd": job.jd,
        "key_skills": job.key_skills,
        "additional_skills": job.additional_skills,
        "openings": job.openings,
        "posted_date": posted_date,
        "closing_date": job.closing_date,
        "status": job.status,
        "approved_by": job.approved_by,
        "approved_date": job.approved_date
    })
    db.commit()
    job_id = result.scalar()  # Get inserted job ID
    return job_id


def get_active_jobs(db: Session):
    query = text("""
        SELECT job_id, created_by, title, job_code, department, location,
               employment_type, experience_required, salary_range, jd,
               key_skills, additional_skills, openings, posted_date,
               closing_date, status, approved_by, approved_date
        FROM jobs
        WHERE status = 'open'
        ORDER BY posted_date DESC
    """)
    
    result = db.execute(query)
    jobs = [dict(row) for row in result.fetchall()]
    return jobs
