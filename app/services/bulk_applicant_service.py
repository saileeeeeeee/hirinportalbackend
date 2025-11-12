# app/services/bulk_applicant_service.py
import os
import re
import shutil
import logging
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any

import PyPDF2
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import UploadFile, HTTPException

# === Import helpers from applicant_service ===
from .applicant_service import (
    save_resume,
    trigger_evaluate_resume_match,
    get_jd,
    get_high_priority_keywords,
    get_normal_keywords,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)


def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        logging.error(f"PDF read error: {e}")
        return ""


def parse_resume_pdf(text: str) -> Dict[str, Any]:
    text = text.replace("\0", " ").strip()
    data: Dict[str, Any] = {
        "first_name": "", "last_name": "", "email": "", "phone": "", "linkedin_url": "",
        "experience_years": 0.0, "education": "", "current_company": "", "current_role": "",
        "skills": ""
    }

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Name
    for line in lines[:5]:
        if re.match(r"^[A-Za-z\s\.\-]+$", line) and len(line.split()) <= 4:
            name_parts = re.findall(r"[A-Za-z]+", line)
            if len(name_parts) >= 2:
                data["first_name"] = name_parts[0]
                data["last_name"] = " ".join(name_parts[1:3])
                break
            elif name_parts:
                data["first_name"] = name_parts[0]
                break

    # Email
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if email_match:
        data["email"] = email_match.group(0).lower()

    # Phone
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if phone_match:
        data["phone"] = re.sub(r"\D", "", phone_match.group(0))[-10:]

    # LinkedIn
    linkedin_match = re.search(r"linkedin\.com/in/[A-Za-z0-9\-_%]+", text, re.I)
    if linkedin_match:
        data["linkedin_url"] = "https://" + linkedin_match.group(0)

    # Experience
    exp_section = re.search(r"(Experience|Work History|Professional Experience)[\s\S]*?(?=(\n[A-Z]|$))", text, re.I)
    total_years = 0.0
    current_job = None

    if exp_section:
        exp_text = exp_section.group(0)
        jobs = re.split(r"\n\s*\n", exp_text)
        job_entries = []

        for job in jobs:
            if not job.strip(): continue
            company_match = re.search(r"at\s+([A-Za-z0-9\s&.,]+?)(?:\n|\||$)", job, re.I)
            role_match = re.search(r"^([A-Za-z\s&.,]+?)(?:\n|at|\|)", job, re.I)
            date_match = re.findall(r"(\d{4})\s*[-–to]+\s*(\d{4}|Present|Current)", job, re.I)

            company = company_match.group(1).strip() if company_match else ""
            role = role_match.group(1).strip() if role_match else ""

            years = 0.0
            if date_match:
                start, end = date_match[0]
                try:
                    start_year = int(start)
                    end_year = datetime.now().year if end.lower() in ["present", "current"] else int(end)
                    years = max(0, end_year - start_year)
                except:
                    years = 0
            total_years += years
            job_entries.append({"company": company, "role": role, "years": years})

        if job_entries:
            current_job = job_entries[0]
            data["current_company"] = current_job["company"]
            data["current_role"] = current_job["role"]

    data["experience_years"] = round(total_years, 1)

    # Skills
    skills_section = re.search(r"Skills?[\s:]+([^.\n}]+)", text, re.I)
    if skills_section:
        raw_skills = skills_section.group(1)
        skills = [s.strip() for s in raw_skills.replace("•", ",").split(",") if s.strip()]
        data["skills"] = ", ".join(skills[:20])

    # Education
    edu_section = re.search(r"(Education|Academic|Qualification)[\s\S]*?(?=(\n[A-Z]|$))", text, re.I)
    if edu_section:
        edu_text = edu_section.group(0)
        degree_match = re.search(r"(B\.Tech|M\.Tech|BSc|MSc|BE|ME|B\.E\.|M\.E\.|Bachelor|Master|PhD)", edu_text, re.I)
        if degree_match:
            data["education"] = degree_match.group(0)

    return data


def create_applicant_from_pdf(
    db: Session,
    pdf_file: UploadFile,
    job_id: int,
    source: str,
    expected_ctc: Optional[float] = None,
    notice_period_days: Optional[int] = None,
    application_status: str = "pending",
    assigned_hr: Optional[str] = None,
    assigned_manager: Optional[str] = None,
    comments: Optional[str] = None,
) -> Dict[str, Any]:
    if not pdf_file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")

    tmp_path = None
    final_path = None
    try:
        # 1. Save to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(pdf_file.file, tmp)
            tmp_path = tmp.name

        # 2. Extract text
        raw_text = extract_text_from_pdf(tmp_path)
        if not raw_text.strip():
            raise HTTPException(400, "Empty PDF content")

        # 3. Parse resume
        parsed = parse_resume_pdf(raw_text)
        if not parsed["email"]:
            raise HTTPException(400, "Email not found in resume")
        if not parsed["first_name"]:
            raise HTTPException(400, "Name not found in resume")

        now = datetime.now()

        # === START TRANSACTION ===
        with db.begin():
            # 4. INSERT applicant with OUTPUT
            applicant_data = {
                "first_name": parsed["first_name"],
                "last_name": parsed["last_name"] or "Applicant",
                "email": parsed["email"],
                "phone": parsed["phone"],
                "linkedin_url": parsed["linkedin_url"],
                "experience_years": parsed["experience_years"],
                "education": parsed["education"],
                "current_company": parsed["current_company"],
                "current_role": parsed["current_role"],
                "expected_ctc": expected_ctc or 0.0,
                "notice_period_days": notice_period_days or 0,
                "skills": parsed["skills"],
                "location": "",
                "resume_url": None,
                "updated_at": now
            }

            insert_sql = text("""
                INSERT INTO applicants (
                    first_name, last_name, email, phone, linkedin_url,
                    experience_years, education, current_company, current_role,
                    expected_ctc, notice_period_days, skills, location,
                    resume_url, updated_at
                )
                OUTPUT INSERTED.applicant_id
                VALUES (
                    :first_name, :last_name, :email, :phone, :linkedin_url,
                    :experience_years, :education, :current_company, :current_role,
                    :expected_ctc, :notice_period_days, :skills, :location,
                    :resume_url, :updated_at
                )
            """)

            result = db.execute(insert_sql, applicant_data)
            applicant_id = result.scalar()
            if not applicant_id:
                raise HTTPException(500, "Failed to insert applicant - no ID returned")

            # 5. SAVE RESUME
            final_path = save_resume(pdf_file, applicant_id=applicant_id)
            logging.info(f"Resume saved at: {final_path}")

            # 6. UPDATE resume_url
            db.execute(
                text("UPDATE applicants SET resume_url = :url WHERE applicant_id = :id"),
                {"url": final_path, "id": applicant_id}
            )

            # 7. INSERT application
            app_params = {
                "applicant_id": applicant_id,
                "job_id": job_id,
                "application_status": application_status,
                "source": source,
                "assigned_hr": assigned_hr or "Unassigned",
                "assigned_manager": assigned_manager or "Unassigned",
                "comments": comments,
                "updated_at": now
            }
            db.execute(text("""
                INSERT INTO applications (
                    applicant_id, job_id, application_status, source,
                    assigned_hr, assigned_manager, comments, updated_at
                ) VALUES (
                    :applicant_id, :job_id, :application_status, :source,
                    :assigned_hr, :assigned_manager, :comments, :updated_at
                )
            """), app_params)

            # 8. EVALUATE
            eval_result = trigger_evaluate_resume_match(
                resume_pdf_path=final_path,
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
                db=db,
            )

        return {
            "applicant_id": applicant_id,
            "resume_url": final_path,
            "expected_ctc": expected_ctc or 0.0,
            "notice_period_days": notice_period_days or 0,
            "assigned_hr": assigned_hr,
            "assigned_manager": assigned_manager,
            "comments": comments,
            "evaluation_result": eval_result,
            "parsed": parsed
        }

    except Exception as e:
        logging.error(f"Single upload failed: {e}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(500, f"Failed to process resume: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass







