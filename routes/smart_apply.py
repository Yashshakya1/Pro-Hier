from fastapi import APIRouter, UploadFile, File, Form
from agents.smart_apply_agent import smart_apply_agent
import shutil, os

router = APIRouter()

@router.post("/smart-apply")
async def smart_apply(
    file: UploadFile = File(...),
    job_title: str = Form(...),
    company_name: str = Form(...),
    jd_text: str = Form(...)
):
    # Save temp file
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = smart_apply_agent.invoke({
        "resume_text": temp_path,
        "job_title": job_title,
        "company_name": company_name,
        "jd_text": jd_text,
        "match_score": 0,
        "match_reasons": [],
        "cover_letter": "",
        "application_status": ""
    })

    os.remove(temp_path)

    return {
        "match_score": result["match_score"],
        "match_reasons": result["match_reasons"],
        "cover_letter": result["cover_letter"],
        "application_status": result["application_status"]
    }