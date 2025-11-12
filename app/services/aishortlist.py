import re
import logging
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, util
import nltk
from nltk.corpus import stopwords
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from fastapi import HTTPException, Depends
from app.config import settings
from app.db.connection import get_db

# Download stopwords if not already present
#nltk.download('stopwords')

# Load the embedding model and stopwords
MODEL = SentenceTransformer('all-MiniLM-L6-v2')
STOPWORDS = set(stopwords.words('english'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_resume_match(resume_pdf_path, jd_text, high_priority_keywords, normal_keywords, 
                          job_id, applicant_id, source, application_status, assigned_hr=None, 
                          assigned_manager=None, comments=None, db: Session = Depends(get_db)):
    """
    Evaluates a resume match against a job description and stores the results in the database.
    
    Parameters:
    - resume_pdf_path: Path to the resume PDF.
    - jd_text: Job description text.
    - high_priority_keywords: Set of high-priority keywords (e.g., technical skills).
    - normal_keywords: Set of normal keywords (e.g., soft skills).
    - job_id: ID of the job.
    - applicant_id: ID of the applicant.
    - source: Source where the application came from (e.g., LinkedIn).
    - application_status: Current status of the application (e.g., applied, shortlisted).
    - assigned_hr: HR manager assigned to the application.
    - assigned_manager: Hiring manager assigned to the application.
    - comments: Any additional comments.
    - db: Database session dependency from FastAPI (injects the session).
    
    Returns:
    - A dictionary with the evaluation results.
    """
    
    # Helper function to extract text from the PDF
    def extract_text_from_pdf(file_path):
        reader = PdfReader(file_path)
        return "".join(page.extract_text() or "" for page in reader.pages)

    # Helper function to preprocess text (lowercase, remove special characters, and stopwords)
    def preprocess_text(text):
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        tokens = text.split()
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
        return " ".join(tokens)

    # Helper function to compute semantic similarity between the resume and job description
    def compute_overall_similarity(resume_text, jd_text):
        embeddings = MODEL.encode([resume_text, jd_text], convert_to_tensor=True)
        similarity = util.cos_sim(embeddings[0], embeddings[1])
        return round(float(similarity[0]), 4)

    # Helper function to compute weighted keyword match score
    def compute_weighted_keyword_score(resume_text, jd_text, high_priority_keywords, normal_keywords):
        resume_tokens = set(resume_text.split())
        jd_tokens = set(jd_text.split())

        high_score = sum(1 for word in resume_tokens if word in jd_tokens and word in high_priority_keywords)
        normal_score = sum(1 for word in resume_tokens if word in jd_tokens and word in normal_keywords)

        high_weight = high_score / len(high_priority_keywords) if high_priority_keywords else 0
        normal_weight = normal_score / len(normal_keywords) if normal_keywords else 0

        combined_score = 0.7 * high_weight + 0.3 * normal_weight
        return round(combined_score, 4)

    # Extract resume text and preprocess both resume and JD text
    resume_raw = extract_text_from_pdf(resume_pdf_path)
    resume_clean = preprocess_text(resume_raw)
    jd_clean = preprocess_text(jd_text)

    # Calculate semantic similarity and weighted keyword match score
    semantic_similarity = compute_overall_similarity(resume_clean, jd_clean)
    keyword_score = compute_weighted_keyword_score(resume_clean, jd_clean, high_priority_keywords, normal_keywords)

    # Final score combining both semantic similarity and keyword match score
    resume_overall_score = round((0.6 * semantic_similarity + 0.4 * keyword_score), 4)

    # Log the results
    logger.info(f"Semantic Similarity: {semantic_similarity}")
    logger.info(f"Keyword Match Score: {keyword_score}")
    logger.info(f"Overall Resume Score: {resume_overall_score}")

    # Insert results into the database using text() for parameterized SQL query
    try:
        sql_query = text("""
            INSERT INTO applications 
            (job_id, applicant_id, applied_date, source, skills_matching_score, jd_matching_score, 
            resume_overall_score, application_status, assigned_hr, assigned_manager, comments, updated_at)
            VALUES
            (:job_id, :applicant_id, :applied_date, :source, :skills_matching_score, :jd_matching_score, 
            :resume_overall_score, :application_status, :assigned_hr, :assigned_manager, :comments, :updated_at)
        """)

        db.execute(sql_query, {
            "job_id": job_id,
            "applicant_id": applicant_id,
            "applied_date": datetime.utcnow(),  # Current date for applied date
            "source": source,
            "skills_matching_score": keyword_score,
            "jd_matching_score": semantic_similarity,
            "resume_overall_score": resume_overall_score,
            "application_status": application_status,
            "assigned_hr": assigned_hr,
            "assigned_manager": assigned_manager,
            "comments": comments,
            "updated_at": datetime.utcnow()  # Current date for updated_at
        })
        
        db.commit()  # Commit the transaction
        logger.info("Application successfully inserted into the database.")

    except Exception as e:
        logger.error(f"Error while inserting into the database: {e}")
        db.rollback()  # Rollback the transaction on error
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {str(e)}")

    # Return the results
    return {
        "semantic_similarity": semantic_similarity,
        "keyword_match_score": keyword_score,
        "resume_overall_score": resume_overall_score,
        "resume_excerpt": resume_clean[:300],
        "jd_excerpt": jd_clean[:300]
    }





