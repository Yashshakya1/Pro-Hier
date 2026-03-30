from fastapi import APIRouter, UploadFile, File, Form
from agents.skill_gap_agent import skill_gap_agent
from pydantic import BaseModel
import shutil, os

router = APIRouter()

@router.post("/skill-gap")
async def analyze_skill_gap(
    file: UploadFile = File(...),
    jd_text: str = Form(...)
):
    # Save uploaded file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    if temp_path.endswith(".docx"):
        from docx import Document
        doc = Document(temp_path)
        resume_text = "\n".join([para.text for para in doc.paragraphs])
    else:
        import pdfplumber
        resume_text = ""
        with pdfplumber.open(temp_path) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text() or ""

    os.remove(temp_path)

    result = skill_gap_agent.invoke({
        "resume_text": resume_text,
        "jd_text": jd_text,
        "resume_skills": [],
        "required_skills": [],
        "matched_skills": [],
        "missing_skills": [],
        "resources": {},
        "gap_score": 0
    })

    return {
        "gap_score": result["gap_score"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "learning_resources": result["resources"]
    }