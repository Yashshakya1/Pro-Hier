from fastapi import APIRouter
from agents.cover_letter_agent import generate_custom_cover_letter, CoverLetterRequest

router = APIRouter()

@router.post("/cover-letter")
async def create_cover_letter(request: CoverLetterRequest):
    letter = generate_custom_cover_letter(request)
    return {"cover_letter": letter}
