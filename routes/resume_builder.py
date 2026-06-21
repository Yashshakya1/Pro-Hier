"""
Resume Builder Routes — ProHire AI
All endpoints for the new Resume Builder feature.
Completely separate from the existing Resume Analyzer (/api/v1/resume).
"""
import os
# Fix: Ensure WeasyPrint can locate GTK/Homebrew libraries on macOS (bypassing SIP stripping)
if os.name == 'posix' and os.path.exists('/opt/homebrew/lib'):
    os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = '/opt/homebrew/lib:' + os.environ.get('DYLD_FALLBACK_LIBRARY_PATH', '')

import json
import uuid
import base64
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agents.resume_builder_agent import resume_builder_agent

router = APIRouter()

# ── Free / Pro Config ─────────────────────────────────────────────────
PRO_ONLY_TEMPLATES = [
    "modern_creative", "executive",
    "tech_developer", "designer_portfolio", "corporate_premium"
]
FREE_MONTHLY_DOWNLOAD_LIMIT = 1

# ── In-memory draft store (fine for demo; replace with Firebase in prod) ─
# Structure: { user_id: { draft_data } }
_draft_store: dict = {}
_usage_store: dict = {}   # { user_id: { "month": "2025-01", "downloads": 0 } }


# ══════════════════════════════════════════════════════════════════════
# Pydantic Models
# ══════════════════════════════════════════════════════════════════════

class PersonalInfo(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    photo_url: str = ""

class ExperienceItem(BaseModel):
    title: str = ""
    company: str = ""
    duration: str = ""
    bullets: List[str] = []

class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""
    grade: str = ""

class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    tech_stack: str = ""
    link: str = ""

class CertificationItem(BaseModel):
    name: str = ""
    issuer: str = ""
    year: str = ""

class DraftPayload(BaseModel):
    user_id: str
    template_id: str = "simple_professional"
    personal_info: PersonalInfo = PersonalInfo()
    summary: str = ""
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    projects: List[ProjectItem] = []
    certifications: List[CertificationItem] = []
    section_order: List[str] = [
        "summary", "experience", "education", "skills", "projects", "certifications"
    ]

class EnhanceRequest(BaseModel):
    user_id: str
    is_pro: bool = False
    job_title: str = ""
    summary: str = ""
    experience: List[ExperienceItem] = []
    skills: List[str] = []

class GeneratePDFRequest(BaseModel):
    user_id: str
    is_pro: bool = False
    template_id: str = "simple_professional"
    personal_info: PersonalInfo = PersonalInfo()
    summary: str = ""
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    projects: List[ProjectItem] = []
    certifications: List[CertificationItem] = []
    section_order: List[str] = [
        "summary", "experience", "education", "skills", "projects", "certifications"
    ]

class SwitchTemplateRequest(BaseModel):
    user_id: str
    template_id: str
    is_pro: bool = False


# ══════════════════════════════════════════════════════════════════════
# Helper: check Pro access for template
# ══════════════════════════════════════════════════════════════════════
def _require_pro_for_template(template_id: str, is_pro: bool):
    # Temporarily free for testing
    return


# ══════════════════════════════════════════════════════════════════════
# Helper: check monthly download limit (free users)
# ══════════════════════════════════════════════════════════════════════
def _check_download_limit(user_id: str, is_pro: bool):
    # Temporarily unlimited for testing
    return

def _increment_download_limit(user_id: str, is_pro: bool):
    if is_pro:
        return
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = _usage_store.get(user_id, {"month": current_month, "downloads": 0})
    if usage["month"] != current_month:
        usage = {"month": current_month, "downloads": 0}
    usage["downloads"] += 1
    _usage_store[user_id] = usage


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT 1: Get All Templates
# ══════════════════════════════════════════════════════════════════════
@router.get("/resume-builder/templates")
def get_templates():
    templates = [
        # ── FREE ──────────────────────────────────────────────────────
        {
            "id": "simple_professional",
            "name": "Simple Professional",
            "description": "Clean, single-column layout. Perfect for corporate jobs.",
            "is_pro": False,
            "has_photo": False,
            "accent_color": "#4F46E5",
            "preview_emoji": "📄",
            "category": "Classic"
        },
        {
            "id": "basic_classic",
            "name": "Basic Classic",
            "description": "Traditional two-tone header. ATS-friendly and timeless.",
            "is_pro": False,
            "has_photo": False,
            "accent_color": "#0891B2",
            "preview_emoji": "📋",
            "category": "Classic"
        },
        {
            "id": "compact_fresher",
            "name": "Compact Fresher",
            "description": "One-page layout ideal for students and fresh graduates.",
            "is_pro": False,
            "has_photo": False,
            "accent_color": "#059669",
            "preview_emoji": "🎓",
            "category": "Fresher"
        },

        # ── PRO ───────────────────────────────────────────────────────
        {
            "id": "modern_creative",
            "name": "Modern Creative",
            "description": "Two-column with circular photo. Vibrant purple accent.",
            "is_pro": True,
            "has_photo": True,
            "accent_color": "#818CF8",
            "preview_emoji": "✨",
            "category": "Creative"
        },
        {
            "id": "executive",
            "name": "Executive Premium",
            "description": "Bold header bar. Designed for senior professionals.",
            "is_pro": True,
            "has_photo": True,
            "accent_color": "#1E3A5F",
            "preview_emoji": "💼",
            "category": "Executive"
        },
        {
            "id": "tech_developer",
            "name": "Tech Developer",
            "description": "Dark sidebar, skill bars, GitHub links. Perfect for engineers.",
            "is_pro": True,
            "has_photo": False,
            "accent_color": "#10B981",
            "preview_emoji": "💻",
            "category": "Tech"
        },
        {
            "id": "designer_portfolio",
            "name": "Designer Portfolio",
            "description": "Large photo header, creative layout for designers.",
            "is_pro": True,
            "has_photo": True,
            "accent_color": "#F472B6",
            "preview_emoji": "🎨",
            "category": "Creative"
        },
        {
            "id": "corporate_premium",
            "name": "Corporate Premium",
            "description": "Two-column with navy sidebar. For finance & consulting.",
            "is_pro": True,
            "has_photo": True,
            "accent_color": "#1E3A5F",
            "preview_emoji": "🏢",
            "category": "Executive"
        },
    ]
    return {"templates": templates, "total": len(templates)}


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT 2: Save / Update Draft
# ══════════════════════════════════════════════════════════════════════
@router.post("/resume-builder/draft")
def save_draft(payload: DraftPayload):
    data = payload.dict()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _draft_store[payload.user_id] = data
    return {"success": True, "message": "Draft saved successfully.", "user_id": payload.user_id}


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT 3: Get Draft
# ══════════════════════════════════════════════════════════════════════
@router.get("/resume-builder/draft/{user_id}")
def get_draft(user_id: str):
    draft = _draft_store.get(user_id)
    if not draft:
        return {"found": False, "draft": None}
    return {"found": True, "draft": draft}


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT 4: Switch Template (keep data)
# ══════════════════════════════════════════════════════════════════════
@router.put("/resume-builder/draft/template")
def switch_template(req: SwitchTemplateRequest):
    _require_pro_for_template(req.template_id, req.is_pro)

    draft = _draft_store.get(req.user_id)
    if draft:
        draft["template_id"] = req.template_id
        draft["updated_at"] = datetime.now(timezone.utc).isoformat()
        _draft_store[req.user_id] = draft

    return {"success": True, "template_id": req.template_id}


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT 5: AI Enhance Content
# ══════════════════════════════════════════════════════════════════════
@router.post("/resume-builder/enhance")
async def enhance_content(req: EnhanceRequest):
    try:
        initial_state = {
            "summary": req.summary,
            "experience": [e.dict() for e in req.experience],
            "skills": req.skills,
            "is_pro": req.is_pro,
            "job_title": req.job_title or "Software Engineer",
            "enhanced_summary": "",
            "enhanced_experience": [],
            "suggested_skills": [],
            "error": None,
        }

        result = resume_builder_agent.invoke(initial_state)

        return {
            "success": True,
            "enhanced_summary":    result.get("enhanced_summary", req.summary),
            "enhanced_experience": result.get("enhanced_experience", [e.dict() for e in req.experience]),
            "suggested_skills":    result.get("suggested_skills", []),   # [] for free users
            "is_pro":              req.is_pro,
            "error":               result.get("error"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI enhancement failed: {str(e)}")


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT 6: Upload Photo
# ══════════════════════════════════════════════════════════════════════
@router.post("/resume-builder/upload-photo")
async def upload_photo(
    user_id: str,
    is_pro: bool = False,
    file: UploadFile = File(...)
):
    # Temporarily free for testing
    is_pro = True
    if not is_pro:
        raise HTTPException(
            status_code=403,
            detail={"error": "pro_required", "message": "Photo upload is available for Pro users only."}
        )

    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images are allowed.")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="Image must be under 5MB.")

    try:
        from PIL import Image

        img = Image.open(BytesIO(contents))
        # Crop to square (center crop)
        w, h = img.size
        min_dim = min(w, h)
        left  = (w - min_dim) // 2
        top   = (h - min_dim) // 2
        img   = img.crop((left, top, left + min_dim, top + min_dim))
        img   = img.resize((400, 400), Image.LANCZOS)

        # Convert to base64 for direct embedding (frontend can also upload to Firebase Storage)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=88)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        photo_url = f"data:image/jpeg;base64,{b64}"

        return {"success": True, "photo_url": photo_url}

    except ImportError:
        # Pillow not installed — return raw base64
        b64 = base64.b64encode(contents).decode("utf-8")
        photo_url = f"data:image/{file.content_type.split('/')[-1]};base64,{b64}"
        return {"success": True, "photo_url": photo_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo processing failed: {str(e)}")


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT 7: Generate PDF
# ══════════════════════════════════════════════════════════════════════
@router.post("/resume-builder/generate-pdf")
async def generate_pdf(req: GeneratePDFRequest):
    # Access control
    _require_pro_for_template(req.template_id, req.is_pro)
    _check_download_limit(req.user_id, req.is_pro)

    try:
        from jinja2 import Environment, FileSystemLoader
        import weasyprint

        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "resume")
        env = Environment(loader=FileSystemLoader(template_dir))

        template_file = f"{req.template_id}.html"
        try:
            template = env.get_template(template_file)
        except Exception:
            # Fallback to simple_professional if template file missing
            template = env.get_template("simple_professional.html")

        html_content = template.render(
            personal_info = req.personal_info.dict(),
            summary       = req.summary,
            experience    = [e.dict() for e in req.experience],
            education     = [e.dict() for e in req.education],
            skills        = req.skills,
            projects      = [p.dict() for p in req.projects],
            certifications= [c.dict() for c in req.certifications],
            section_order = req.section_order,
        )

        # Write to temp file
        tmp_dir  = tempfile.mkdtemp()
        pdf_path = os.path.join(tmp_dir, f"resume_{req.user_id[:8]}.pdf")

        pdf = weasyprint.HTML(string=html_content).write_pdf()
        with open(pdf_path, "wb") as f:
            f.write(pdf)

        # Increment count only after the PDF is successfully generated and written
        _increment_download_limit(req.user_id, req.is_pro)

        return FileResponse(
            path        = pdf_path,
            media_type  = "application/pdf",
            filename    = f"{req.personal_info.full_name.replace(' ', '_') or 'Resume'}.pdf",
        )

    except ImportError:
        # WeasyPrint not installed — return HTML as fallback
        raise HTTPException(
            status_code=503,
            detail="PDF generation not available on this server. Please install weasyprint."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
