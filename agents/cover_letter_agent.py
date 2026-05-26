from pydantic import BaseModel
from utils.llm_client import llm

class CoverLetterRequest(BaseModel):
    resume_text: str
    job_role: str
    company_name: str

def generate_custom_cover_letter(data: CoverLetterRequest) -> str:
    prompt = f"""
    You are an expert career coach and professional copywriter.
    Write a highly persuasive, modern, and concise cover letter (max 250 words) for the following applicant.
    
    Target Company: {data.company_name}
    Target Role: {data.job_role}
    
    Candidate's Resume/Skills: 
    {data.resume_text}
    
    Instructions:
    - Do not use generic, outdated formats (like "To Whom It May Concern"). Start with a strong enthusiastic opening.
    - Highlight specific skills from the resume that align perfectly with the target role.
    - Keep it under 250 words, highly professional, confident, and action-oriented.
    - Omit physical address blocks, just output the letter body and sign-off.
    
    Output ONLY the letter text. No introductory remarks.
    """
    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error generating cover letter: {str(e)}"
