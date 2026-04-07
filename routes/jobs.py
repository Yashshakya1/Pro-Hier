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
        print(f"🚀 [JOBS] Starting search for: {field} in {location}")
        result = job_agent.invoke({
            "resume_text": resume_text,
            "field": field,
            "location": location,
            "country": country,
            "user_type": user_type,
            "profile_summary": "",
            "jobs": [],
            "best_match": {},
            "tips": "",
            "boost_keywords": []
        })
        
        print(f"✅ [JOBS] Found {len(result.get('jobs', []))} potential matches.")
        
        return {
            "profile_summary": result.get("profile_summary", ""),
            "jobs": result.get("jobs", []),
            "best_match": result.get("best_match", {}),
            "tips": result.get("tips", ""),
            "boost_keywords": result.get("boost_keywords", [])
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ [JOBS ERROR] Crashed during agent execution:\n{error_details}")
        # Return a 200 with error details so the frontend can display the ACTUAL error
        return {
            "error": str(e),
            "details": "AI Agent failed to process your request. Check backend logs.",
            "jobs": []
        }

@router.post("/alert-check")
async def alert_check(request: Request):
    """
    Optimized endpoint for background job alerts.
    """
    data = await request.json()
    resume_text = data.get("resume_text", "")
    field = data.get("field", "")
    location = data.get("location", "")
    country = data.get("country", "India")
    user_type = data.get("user_type", "Fresher")

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
            "tips": "",
            "boost_keywords": []
        })
        
        best_match = result.get("best_match", {})
        score = int(best_match.get("match_score", 0))
        
        if score >= 90:
            # Detect type
            is_internship = "intern" in best_match.get("role", "").lower() or user_type == "Student"
            job_type = "internship" if is_internship else "job"
            
            return {
                "new_match": True,
                "job": best_match,
                "type": job_type,
                "boost_keywords": result.get("boost_keywords", [])
            }
            
        return {"new_match": False}
    except Exception as e:
        return {"error": str(e)}
