from fastapi import APIRouter
from agents.smart_apply_agent import smart_apply_agent
from pydantic import BaseModel

router = APIRouter()

class SmartApplyRequest(BaseModel):
    resume_text: str
    job_title: str
    company_name: str
    jd_text: str

@router.post("/smart-apply")
async def smart_apply(request: SmartApplyRequest):
    result = smart_apply_agent.invoke({
        "resume_text": request.resume_text,
        "job_title": request.job_title,
        "company_name": request.company_name,
        "jd_text": request.jd_text,
        "match_score": 0,
        "match_reasons": [],
        "cover_letter": "",
        "application_status": ""
    })
    
    return {
        "match_score": result["match_score"],
        "match_reasons": result["match_reasons"],
        "cover_letter": result["cover_letter"],
        "application_status": result["application_status"]
    }