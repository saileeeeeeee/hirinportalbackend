# app/services/job_service.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.v1.hr.schemas import JobCreate, JobRequestCreate, JobRequestResponse, JobRequestUpdate
from fastapi import HTTPException
from datetime import datetime
from typing import Optional, List, Dict, Any

# ==============================
#       JOB POSTING LOGIC
# ==============================

def get_active_jobs(db: Session) -> List[Dict[str, Any]]:
    query = text("""
        SELECT 
            job_id, created_by, title, job_code, department, location,
            employment_type, experience_required, salary_range, jd,
            key_skills, additional_skills, openings, posted_date,
            closing_date, status, approved_by, approved_date
        FROM jobs 
        WHERE status = 'open'
        ORDER BY posted_date DESC
    """)
    result = db.execute(query).mappings().fetchall()
    return [dict(row) for row in result]


def create_job(db: Session, job: JobCreate) -> Dict[str, Any]:
    if job.approved_by:
        user_check = db.execute(
            text("SELECT emp_id FROM users WHERE emp_id = :emp_id"),
            {"emp_id": job.approved_by}
        ).fetchone()
        if not user_check:
            raise HTTPException(status_code=400, detail=f"Approver with emp_id {job.approved_by} not found.")

    insert_query = text("""
        INSERT INTO jobs (
            created_by, title, job_code, department, location, employment_type,
            experience_required, salary_range, jd, key_skills, additional_skills,
            openings, posted_date, closing_date, status, approved_by, approved_date
        ) VALUES (
            :created_by, :title, :job_code, :department, :location, :employment_type,
            :experience_required, :salary_range, :jd, :key_skills, :additional_skills,
            :openings, :posted_date, :closing_date, :status, :approved_by, :approved_date
        )
    """)

    posted_date = job.posted_date or datetime.now()

    try:
        db.execute(insert_query, {
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
        return {"message": "Job created successfully", "status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating job: {str(e)}")


def get_job_by_id(db: Session, job_id: int) -> Dict[str, Any]:
    query = text("""
        SELECT 
            job_id, created_by, title, job_code, department, location,
            employment_type, experience_required, salary_range, jd,
            key_skills, additional_skills, openings, posted_date,
            closing_date, status, approved_by, approved_date
        FROM jobs 
        WHERE job_id = :job_id
    """)
    result = db.execute(query, {"job_id": job_id}).mappings().fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(result)


# ==============================
#       JOB REQUEST LOGIC
# ==============================

def _get_manager_id_by_name(db: Session, manager_name: str) -> int:
    """
    Search `users` table for a Manager by full_name or username.
    Returns emp_id if found, else raises 404.
    """
    sql = text("""
        SELECT emp_id FROM users 
        WHERE (full_name = :name OR username = :name)
          AND status = 'active'
    """)
    result = db.execute(sql, {"name": manager_name.strip()}).fetchone()
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Manager with name '{manager_name}' not found or not active."
        )
    try:
        return result.emp_id
    except Exception:
        # fallback when result is tuple-like
        return list(result)[0]


def create_job_request(db: Session, payload: JobRequestCreate) -> JobRequestResponse:
    """
    Create Job_Request using manager_name → lookup → manager_id.
    Uses OUTPUT INSERTED.JD_ID (SQL Server) or may be adapted to RETURNING for Postgres.
    """
    # Resolve manager_name → manager_id
    try:
        manager_id = _get_manager_id_by_name(db, payload.manager_name)
    except HTTPException:
        raise  # re-raise 404

    # NOTE: This uses SQL Server OUTPUT. If you're using Postgres, replace with RETURNING JD_ID.
    insert_sql = text("""
        INSERT INTO Job_Request (
            manager_id, JobTitle, JobDescription,
            MinExperienceYears, MaxExperienceYears,
            KeySkills, AdditionalSkills,
            TotalVacancy, management_approval
        )
        OUTPUT INSERTED.JD_ID
        VALUES (
            :manager_id, :JobTitle, :JobDescription,
            :MinExperienceYears, :MaxExperienceYears,
            :KeySkills, :AdditionalSkills,
            :TotalVacancy, :management_approval
        );
    """)

    params = {
        "manager_id": manager_id,
        "JobTitle": payload.JobTitle,
        "JobDescription": payload.JobDescription,
        "MinExperienceYears": payload.MinExperienceYears,
        "MaxExperienceYears": payload.MaxExperienceYears,
        "KeySkills": payload.KeySkills,
        "AdditionalSkills": payload.AdditionalSkills,
        "TotalVacancy": payload.TotalVacancy,
        "management_approval": 1 if payload.management_approval else 0,
    }

    try:
        # execute the insert which returns the inserted JD_ID via OUTPUT (SQL Server)
        result = db.execute(insert_sql, params)
        new_id_val = result.scalar()  # first column of first row
        db.commit()
        if new_id_val is None:
            raise HTTPException(status_code=500, detail="Failed to obtain inserted JD_ID.")
        new_id = int(new_id_val)
        return get_job_request_by_id(db, new_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def get_job_request_by_id(db: Session, jd_id: int) -> JobRequestResponse:
    sql = text("""
        SELECT 
            JD_ID, manager_id, JobTitle, JobDescription,
            MinExperienceYears, MaxExperienceYears,
            KeySkills, AdditionalSkills,
            TotalVacancy, management_approval
        FROM Job_Request
        WHERE JD_ID = :jd_id
    """)
    row = db.execute(sql, {"jd_id": jd_id}).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job request not found")
    row_dict = dict(row)
    row_dict["management_approval"] = bool(row_dict["management_approval"])
    return JobRequestResponse(**row_dict)


def list_job_requests(db: Session, approved: Optional[bool] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM Job_Request"
    params = {}
    if approved is not None:
        sql += " WHERE management_approval = :approved"
        params["approved"] = 1 if approved else 0
    sql += " ORDER BY JD_ID DESC"

    rows = db.execute(text(sql), params).mappings().fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["management_approval"] = bool(d["management_approval"])
        result.append(d)
    return result


def list_job_requests_by_username(db: Session, username_or_fullname: str, approved: Optional[bool] = None) -> List[Dict[str, Any]]:
    """
    Resolve users.emp_id by username or full_name, then return only Job_Request rows for that manager_id.
    Returns empty list if no matching active user is found.
    """
    sql_user = text("""
        SELECT emp_id FROM users
        WHERE (username = :name OR full_name = :name)
          AND status = 'active'
    """)
    user_row = db.execute(sql_user, {"name": username_or_fullname.strip()}).fetchone()
    if not user_row:
        # Return empty list if user not found; frontend can show "no records"
        return []

    try:
        emp_id = user_row.emp_id
    except Exception:
        emp_id = list(user_row)[0]

    sql = "SELECT * FROM Job_Request WHERE manager_id = :mid"
    params = {"mid": emp_id}
    if approved is not None:
        sql += " AND management_approval = :approved"
        params["approved"] = 1 if approved else 0
    sql += " ORDER BY JD_ID DESC"

    rows = db.execute(text(sql), params).mappings().fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["management_approval"] = bool(d["management_approval"])
        result.append(d)
    return result


def update_job_request_approval(db: Session, jd_id: int, approve: bool) -> JobRequestResponse:
    """
    Toggle/set management_approval for a job request and return updated row.
    """
    sql = text("""
        UPDATE Job_Request
        SET management_approval = :val
        WHERE JD_ID = :jd_id
    """)
    res = db.execute(sql, {"val": 1 if approve else 0, "jd_id": jd_id})
    if res.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Job request not found")
    db.commit()
    return get_job_request_by_id(db, jd_id)


def delete_job_request(db: Session, jd_id: int) -> Dict[str, Any]:
    sql = text("DELETE FROM Job_Request WHERE JD_ID = :jd_id")
    res = db.execute(sql, {"jd_id": jd_id})
    if res.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=404, detail="Job request not found")
    db.commit()
    return {"message": "Job request deleted", "JD_ID": jd_id}


def update_job_request(db: Session, jd_id: int, payload: JobRequestUpdate) -> JobRequestResponse:
    """
    Partial update fields provided in payload. If manager_name provided, resolve to manager_id.
    """
    existing = db.execute(text("SELECT JD_ID FROM Job_Request WHERE JD_ID = :jd_id"), {"jd_id": jd_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Job request not found")

    updates = []
    params = {"jd_id": jd_id}

    if payload.manager_name is not None:
        manager_id = _get_manager_id_by_name(db, payload.manager_name)
        updates.append("manager_id = :manager_id")
        params["manager_id"] = manager_id

    if payload.JobTitle is not None:
        updates.append("JobTitle = :JobTitle")
        params["JobTitle"] = payload.JobTitle
    if payload.JobDescription is not None:
        updates.append("JobDescription = :JobDescription")
        params["JobDescription"] = payload.JobDescription
    if payload.MinExperienceYears is not None:
        updates.append("MinExperienceYears = :MinExperienceYears")
        params["MinExperienceYears"] = payload.MinExperienceYears
    if payload.MaxExperienceYears is not None:
        updates.append("MaxExperienceYears = :MaxExperienceYears")
        params["MaxExperienceYears"] = payload.MaxExperienceYears
    if payload.KeySkills is not None:
        updates.append("KeySkills = :KeySkills")
        params["KeySkills"] = payload.KeySkills
    if payload.AdditionalSkills is not None:
        updates.append("AdditionalSkills = :AdditionalSkills")
        params["AdditionalSkills"] = payload.AdditionalSkills
    if payload.TotalVacancy is not None:
        updates.append("TotalVacancy = :TotalVacancy")
        params["TotalVacancy"] = payload.TotalVacancy
    if payload.management_approval is not None:
        updates.append("management_approval = :management_approval")
        params["management_approval"] = 1 if payload.management_approval else 0

    if not updates:
        return get_job_request_by_id(db, jd_id)  # nothing to update

    set_clause = ", ".join(updates)
    sql = text(f"UPDATE Job_Request SET {set_clause} WHERE JD_ID = :jd_id")

    try:
        res = db.execute(sql, params)
        if res.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail="Job request not found")
        db.commit()
        return get_job_request_by_id(db, jd_id)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update job request: {str(e)}")
