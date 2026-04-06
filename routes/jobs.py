from fastapi import APIRouter, Request, UploadFile, HTTPException
from agents.job_agent import job_agent
import os
import shutil
from utils.pdf_parser import extract_text_from_pdf

router = APIRouter()

@router.post("/find-jobs")
async def find_jobs(request: Request):
    content_type = request.headers.get("content-type", "")
    
    resume_text = ""
    field = ""
    location = ""
    country = "India"
    
    user_type = "Fresher"
    
    if "application/json" in content_type:
        data = await request.json()
        resume_text = data.get("resume_text", "")
        field = data.get("field", "")
        location = data.get("location", "")
        country = data.get("country", "India")
        user_type = data.get("user_type", "Fresher")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        resume_text = form.get("resume_text", "")
        field = form.get("field", "")
        location = form.get("location", "")
        country = form.get("country", "India")
        user_type = form.get("user_type", "Fresher")
        
        file = form.get("file")
        if file and isinstance(file, UploadFile) and file.filename:
            temp_path = f"temp_job_{file.filename}"
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            extracted_text = extract_text_from_pdf(temp_path)
            resume_text = extracted_text + "\n" + (resume_text or "")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    try:
        result = job_agent.invoke({
            "resume_text": resume_text,
            "field": field,
            "location": location,
            "country": country,
            "user_type": user_type,
            "profile_summary": "",
            "jobs": [],
            "best_match": {},
            "tips": ""
        })
        
        return {
            "profile_summary": result.get("profile_summary", ""),
            "jobs": result.get("jobs", []),
            "best_match": result.get("best_match", {}),
            "tips": result.get("tips", "")
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Job Agent Error: {error_details}")
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")
