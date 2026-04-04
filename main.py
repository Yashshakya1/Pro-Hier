from fastapi import FastAPI
from routes.resume import router as resume_router
from routes.interview import router as interview_router
from routes.skill_gap import router as skill_gap_router
from routes.smart_apply import router as smart_apply_router
from routes.internship import router as internship_router
from routes.cover_letter import router as cover_letter_router

app = FastAPI(title="ProHire API 🚀")

app.include_router(resume_router, prefix="/api/v1")
app.include_router(interview_router, prefix="/api/v1")
app.include_router(skill_gap_router, prefix="/api/v1")
app.include_router(smart_apply_router, prefix="/api/v1")
app.include_router(internship_router, prefix="/api/v1")
app.include_router(cover_letter_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "ProHire Backend Running! 🚀"}