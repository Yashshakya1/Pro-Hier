from fastapi import APIRouter
from agents.internship_agent import internship_agent
from pydantic import BaseModel

router = APIRouter()

class InternshipRequest(BaseModel):
    resume_text: str
    field: str
    user_type: str

@router.post("/find-internships")
async def find_internships(request: InternshipRequest):
    result = internship_agent.invoke({
        "resume_text": request.resume_text,
        "field": request.field,
        "user_type": request.user_type,
        "profile_summary": "",
        "internships": [],
        "best_match": {},
        "application_tips": ""
    })
    
    return {
        "profile_summary": result["profile_summary"],
        "internships": result["internships"],
        "best_match": result["best_match"],
        "application_tips": result["application_tips"]
    }