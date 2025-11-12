import os
import re
import shutil
import logging
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any, Set
import PyPDF2
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import UploadFile, HTTPException

logging.basicConfig(level=logging.INFO)

UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_resume_from_temp(tmp_file_path: str, applicant_id: int, original_filename: str) -> str:
    """
    Move/rename the temp file into uploads/resumes with a stable name.
    Avoid re-reading UploadFile.file (which may be at EOF).
    """
    filename = f"{applicant_id}_{original_filename}"
    dest = os.path.join(UPLOAD_DIR, filename)
    # Use shutil.move (rename/move)
    shutil.move(tmp_file_path, dest)
    logging.info(f"Resume moved to: {dest}")
    return dest


def _extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            texts = []
            for page in reader.pages:
                try:
                    t = page.extract_text()
                    if t:
                        texts.append(t)
                except Exception:
                    # page-level extraction failure shouldn't abort everything
                    continue
            return "\n".join(texts)
    except Exception as e:
        logging.error(f"PDF error extracting text from {file_path}: {e}")
        return ""


def _parse_resume_pdf(text: str) -> Dict[str, Any]:
    """
    Best-effort resume parsing. Returns dict with keys used downstream.
    """
    text = text.replace("\0", " ").strip()
    data = {
        "first_name": "", "last_name": "", "email": "", "phone": "", "linkedin_url": "",
        "experience_years": 0.0, "education": "", "current_company": "", "current_role": "", "skills": ""
    }
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Try to parse name from top lines
    for line in lines[:6]:
        # allow letters, dots, hyphens, spaces
        if re.match(r"^[A-Za-z\s\.\-]+$", line) and 1 <= len(line.split()) <= 4:
            parts = re.findall(r"[A-Za-z]+", line)
            if len(parts) >= 2:
                data["first_name"] = parts[0].capitalize()
                data["last_name"] = " ".join(parts[1:3]).capitalize()
                break
            elif parts:
                data["first_name"] = parts[0].capitalize()
                break

    # Email
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if email:
        data["email"] = email.group(0).lower()

    # Phone (last 10 digits normalized)
    phone = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text)
    if phone:
        digits = re.sub(r"\D", "", phone.group(0))
        if len(digits) >= 10:
            data["phone"] = digits[-10:]

    # LinkedIn
    linkedin = re.search(r"(linkedin\.com\/in\/[A-Za-z0-9\-_%.]+)", text, re.I)
    if linkedin:
        url = linkedin.group(1)
        data["linkedin_url"] = url if url.startswith("http") else f"https://{url}"

    # Experience years: naive scan of Experience/Work History block
    exp_block = re.search(r"(Experience|Work History)[\s\S]*?(?=(\n[A-Z][a-z]|$))", text, re.I)
    total_years = 0.0
    if exp_block:
        jobs = re.split(r"\n\s*\n", exp_block.group(0))
        for job in jobs:
            # look for ranges like 2018 - 2021, 2016–Present, Jan 2015 - Dec 2018 etc.
            dates = re.findall(r"(\d{4})\s*[-–to]+\s*(\d{4}|Present|Current)", job, re.I)
            if dates:
                s, e = dates[0]
                try:
                    start_year = int(s)
                    end_year = datetime.now().year if str(e).lower() in ("present", "current") else int(e)
                    if end_year >= start_year:
                        total_years += (end_year - start_year)
                except Exception:
                    continue
    data["experience_years"] = round(total_years, 1)

    # Skills block (first line after "Skills")
    skills = re.search(r"(Skills|Technical Skills|Skillset)[:\s]*([\s\S]{0,400}?)(?=(\n[A-Z][a-z]|$))", text, re.I)
    if skills:
        raw = skills.group(2)
        # replace bullets and newlines with commas then split
        cleaned = raw.replace("•", ",").replace("\n", ",")
        data["skills"] = ", ".join([s.strip() for s in cleaned.split(",") if s.strip()][:30])

    # Education
    edu = re.search(r"(Education|Academic Qualifications)[\s\S]*?(?=(\n[A-Z]|$))", text, re.I)
    if edu:
        deg = re.search(r"(B\.?Tech|M\.?Tech|BSc|MSc|BE|ME|B\.?E\.?|M\.?E\.?|Bachelor|Master|Ph\.?D)", edu.group(0), re.I)
        if deg:
            data["education"] = deg.group(0)

    return data


def _get_jd(job_id: int, db: Session) -> str:
    res = db.execute(text("SELECT jd FROM jobs WHERE job_id = :job_id"), {"job_id": job_id}).fetchone()
    return res[0] if res else ""


def _get_high_priority_keywords(job_id: int, db: Session) -> Set[str]:
    rows = db.execute(text("SELECT key_skills FROM jobs WHERE job_id = :job_id"), {"job_id": job_id}).fetchall()
    return {r[0] for r in rows if r[0]}


def _get_normal_keywords(job_id: int, db: Session) -> Set[str]:
    rows = db.execute(text("SELECT additional_skills FROM jobs WHERE job_id = :job_id"), {"job_id": job_id}).fetchall()
    return {r[0] for r in rows if r[0]}


def _trigger_evaluate_resume_match(**kwargs):
    # imported lazily, keep original behavior
    from .aishortlist import evaluate_resume_match
    try:
        return evaluate_resume_match(**kwargs)
    except Exception as e:
        logging.error(f"AI evaluation failed: {e}")
        # bubble up a HTTPException so callers can produce a failure status code/message
        raise HTTPException(status_code=500, detail=f"AI eval failed: {e}")

def create_applicant_from_pdf(
    db: Session,
    pdf_file: UploadFile,
    job_id: int,
    source: str,
    expected_ctc: Optional[float] = None,
    notice_period_days: Optional[int] = None,
    application_status: str = "pending",
    assigned_hr: Optional[int] = None,
    assigned_manager: Optional[int] = None,
    comments: Optional[str] = None,
) -> Dict[str, Any]:
    if not pdf_file.filename or not pdf_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    tmp_path = None
    final_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(pdf_file.file, tmp)
            tmp_path = tmp.name

        # <-- renamed local variable to avoid shadowing sqlalchemy.text
        extracted_text = _extract_text_from_pdf(tmp_path)
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Empty PDF or text extraction failed")

        parsed = _parse_resume_pdf(extracted_text)
        if not parsed["email"]:
            raise HTTPException(status_code=400, detail="Email not found")
        if not parsed["first_name"]:
            raise HTTPException(status_code=400, detail="Name not found")

        now = datetime.now()

        with db.begin():
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
                raise HTTPException(status_code=500, detail="Failed to create applicant (no id returned)")

            final_path = _save_resume_from_temp(tmp_path, applicant_id, pdf_file.filename)
            db.execute(
                text("UPDATE applicants SET resume_url = :url WHERE applicant_id = :id"),
                {"url": final_path, "id": applicant_id}
            )

            app_sql = text("""
                INSERT INTO applications (
                    applicant_id, job_id, application_status, source,
                    assigned_hr, assigned_manager, comments, updated_at
                ) VALUES (
                    :applicant_id, :job_id, :application_status, :source,
                    :assigned_hr, :assigned_manager, :comments, :updated_at
                )
            """)
            db.execute(app_sql, {
                "applicant_id": applicant_id,
                "job_id": job_id,
                "application_status": application_status,
                "source": source,
                "assigned_hr": assigned_hr,
                "assigned_manager": assigned_manager,
                "comments": comments,
                "updated_at": now
            })

            eval_result = _trigger_evaluate_resume_match(
                resume_pdf_path=final_path,
                jd_text=_get_jd(job_id, db),
                high_priority_keywords=_get_high_priority_keywords(job_id, db),
                normal_keywords=_get_normal_keywords(job_id, db),
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

    except HTTPException:
        logging.exception("HTTPException while creating applicant from PDF")
        if final_path and os.path.exists(final_path):
            try: os.unlink(final_path)
            except: pass
        raise
    except Exception as e:
        logging.exception(f"Upload failed: {e}")
        if final_path and os.path.exists(final_path):
            try: os.unlink(final_path)
            except: pass
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"Failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass
