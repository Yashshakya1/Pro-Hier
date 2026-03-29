from fastapi import APIRouter, UploadFile, File, Form
from agents.resume_agent import resume_agent
import shutil, os

router = APIRouter()

@router.post("/analyze-resume")
async def analyze_resume(
    file: UploadFile = File(...),
    jd_text: str = Form(...)
):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = resume_agent.invoke({
        "pdf_path": temp_path,
        "jd_text": jd_text,
        "resume_text": "",
        "skills": [],
        "jd_keywords": [],
        "ats_score": 0,
        "feedback": ""
    })

    os.remove(temp_path)

    return {
        "ats_score": result["ats_score"],
        "matched_skills": result["skills"],
        "jd_keywords": result["jd_keywords"],
        "feedback": result["feedback"]
    }