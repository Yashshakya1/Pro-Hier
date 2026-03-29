from fastapi import APIRouter
from agents.interview_agent import interview_agent
from pydantic import BaseModel

router = APIRouter()

class InterviewRequest(BaseModel):
    resume_text: str
    job_role: str
    interview_type: str
    user_answer: str

@router.post("/mock-interview")
async def mock_interview(request: InterviewRequest):
    result = interview_agent.invoke({
        "resume_text": request.resume_text,
        "job_role": request.job_role,
        "interview_type": request.interview_type,
        "questions": [],
        "current_question": "",
        "user_answer": request.user_answer,
        "evaluation": "",
        "followup_question": "",
        "final_score": 0,
        "final_feedback": ""
    })
    
    return {
        "question_asked": result["current_question"],
        "followup_question": result["followup_question"],
        "evaluation": result["evaluation"],
        "final_score": result["final_score"],
        "final_feedback": result["final_feedback"],
        "all_questions": result["questions"]
    }