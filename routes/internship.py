from fastapi import APIRouter, Request, UploadFile, HTTPException
from agents.internship_agent import internship_agent
import os
import shutil
from utils.pdf_parser import extract_text_from_pdf

router = APIRouter()

@router.post("/find-internships")
async def find_internships(request: Request):
    content_type = request.headers.get("content-type", "")
    
    resume_text = ""
    field = ""
    user_type = ""
    
    if "application/json" in content_type:
        data = await request.json()
        resume_text = data.get("resume_text", "")
        field = data.get("field", "")
        user_type = data.get("user_type", "")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        resume_text = form.get("resume_text", "")
        field = form.get("field", "")
        user_type = form.get("user_type", "")
        
        file = form.get("file")
        if file and isinstance(file, UploadFile) and file.filename:
            temp_path = f"temp_intern_{file.filename}"
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            extracted_text = extract_text_from_pdf(temp_path)
            resume_text = extracted_text + "\n" + resume_text
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    try:
        result = internship_agent.invoke({
            "resume_text": resume_text,
            "field": field,
            "user_type": user_type,
            "profile_summary": "",
            "internships": [],
            "best_match": {},
            "application_tips": ""
        })
        
        return {
            "profile_summary": result.get("profile_summary", ""),
            "internships": result.get("internships", []),
            "best_match": result.get("best_match", {}),
            "application_tips": result.get("application_tips", "")
        }
    except Exception as e:
        print(f"Agent Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")