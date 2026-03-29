from agents.skill_gap_agent import skill_gap_agent
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SkillGapRequest(BaseModel):
    resume_text: str
    jd_text: str

@router.post("/skill-gap")
async def analyze_skill_gap(request: SkillGapRequest):
    result = skill_gap_agent.invoke({
        "resume_text": request.resume_text,
        "jd_text": request.jd_text,
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