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

class ResumeBasics(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    photo_url: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""

class ResumeWork(BaseModel):
    company: str = ""
    position: str = ""
    duration: str = ""
    highlights: List[str] = []

class ResumeEducation(BaseModel):
    institution: str = ""
    studyType: str = ""
    duration: str = ""

class ResumeProject(BaseModel):
    name: str = ""
    description: str = ""
    url: str = ""

class ResumeCertification(BaseModel):
    name: str = ""
    issuer: str = ""

class JsonResumeModel(BaseModel):
    basics: ResumeBasics = ResumeBasics()
    work: List[ResumeWork] = []
    education: List[ResumeEducation] = []
    skills: List[str] = []
    projects: List[ResumeProject] = []
    certifications: List[ResumeCertification] = []

class DraftPayload(BaseModel):
    user_id: str
    template_id: str = "simple_professional"
    json_resume: JsonResumeModel = JsonResumeModel()

class EnhanceRequest(BaseModel):
    user_id: str
    is_pro: bool = False
    job_title: str = ""
    basics: ResumeBasics = ResumeBasics()
    work: List[ResumeWork] = []
    skills: List[str] = []

class GeneratePDFRequest(BaseModel):
    user_id: str
    is_pro: bool = False
    template_id: str = "simple_professional"
    json_resume: JsonResumeModel = JsonResumeModel()
    accent_color: Optional[str] = None
    font_family: Optional[str] = None

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
    reg_path = os.path.join(os.path.dirname(__file__), "..", "templates_registry.json")
    if os.path.exists(reg_path):
        try:
            with open(reg_path, "r") as f:
                templates = json.load(f)
        except Exception:
            templates = []
    else:
        templates = []
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
        experience_mapped = []
        for e in req.work:
            experience_mapped.append({
                "title": e.position,
                "company": e.company,
                "duration": e.duration,
                "bullets": e.highlights,
            })

        initial_state = {
            "summary": req.basics.summary,
            "experience": experience_mapped,
            "skills": req.skills,
            "is_pro": req.is_pro,
            "job_title": req.job_title or "Software Engineer",
            "enhanced_summary": "",
            "enhanced_experience": [],
            "suggested_skills": [],
            "error": None,
        }

        result = resume_builder_agent.invoke(initial_state)

        enhanced_work = []
        for e in result.get("enhanced_experience", experience_mapped):
            enhanced_work.append({
                "company": e.get("company", ""),
                "position": e.get("title", ""),
                "duration": e.get("duration", ""),
                "highlights": e.get("bullets", []),
            })

        return {
            "success": True,
            "enhanced_summary":    result.get("enhanced_summary", req.basics.summary),
            "enhanced_experience": enhanced_work,
            "suggested_skills":    result.get("suggested_skills", []),
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

    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    content_type = file.content_type
    if content_type == "application/octet-stream" or not content_type:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext in [".jpg", ".jpeg"]:
            content_type = "image/jpeg"
        elif ext == ".png":
            content_type = "image/png"
        elif ext == ".webp":
            content_type = "image/webp"

    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Only JPEG, PNG, or WebP images are allowed. Got content-type: {file.content_type}")

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
    _require_pro_for_template(req.template_id, req.is_pro)
    _check_download_limit(req.user_id, req.is_pro)

    try:
        from jinja2 import Environment, FileSystemLoader
        import weasyprint

        base_id = req.template_id
        accent_color = req.accent_color
        font_style = req.font_family # e.g. "Modern Sans", "Elegant Serif", "Clean Code", "Classic Serif", "Sleek Outfit"
        
        font_map = {
            "Modern Sans": "'Inter', sans-serif",
            "Elegant Serif": "'Playfair Display', Georgia, serif",
            "Clean Code": "'Roboto Mono', monospace",
            "Classic Serif": "'Lora', serif",
            "Sleek Outfit": "'Outfit', sans-serif"
        }
        font_family = font_map.get(font_style) if font_style else None

        if not accent_color:
            reg_path = os.path.join(os.path.dirname(__file__), "..", "templates_registry.json")
            if os.path.exists(reg_path):
                try:
                    with open(reg_path, "r") as f:
                        regs = json.load(f)
                        for r in regs:
                            if r["id"] == base_id:
                                accent_color = r.get("accent_color", "#4F46E5")
                                break
                except Exception:
                    pass
        if not accent_color:
            accent_color = "#4F46E5"

        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "resume")
        env = Environment(loader=FileSystemLoader(template_dir))

        template_file = f"{base_id}.html"
        try:
            template = env.get_template(template_file)
        except Exception:
            template = env.get_template("simple_professional.html")

        # Map standard JSON Resume fields to existing Jinja template variables
        personal_info = {
            "full_name": req.json_resume.basics.name,
            "email": req.json_resume.basics.email,
            "phone": req.json_resume.basics.phone,
            "location": req.json_resume.basics.location,
            "linkedin": req.json_resume.basics.linkedin,
            "github": req.json_resume.basics.github,
            "website": req.json_resume.basics.website,
            "photo_url": req.json_resume.basics.photo_url,
        }
        
        experience = []
        for w in req.json_resume.work:
            experience.append({
                "title": w.position,
                "company": w.company,
                "duration": w.duration,
                "bullets": w.highlights
            })
            
        education = []
        for e in req.json_resume.education:
            education.append({
                "degree": e.studyType,
                "institution": e.institution,
                "year": e.duration,
                "grade": ""
            })
            
        projects = []
        for p in req.json_resume.projects:
            projects.append({
                "name": p.name,
                "description": p.description,
                "tech_stack": "",
                "link": p.url
            })
            
        certifications = []
        for c in req.json_resume.certifications:
            certifications.append({
                "name": c.name,
                "issuer": c.issuer,
                "year": ""
            })

        html_content = template.render(
            personal_info = personal_info,
            summary       = req.json_resume.basics.summary,
            experience    = experience,
            education     = education,
            skills        = req.json_resume.skills,
            projects      = projects,
            certifications= certifications,
            section_order = ["summary", "experience", "education", "skills", "projects", "certifications"],
        )

        # Inject dynamic overrides for color and fonts
        override_style = f"<style>\n"
        if accent_color:
            override_style += f"""
            .sidebar, .header-bar, .header {{ border-color: {accent_color} !important; }}
            .sidebar, .header-bar {{ background: {accent_color} !important; }}
            .section-title, .exp-company, .proj-link, .contact-row a, .contact a, .proj-title a, .proj-title {{ color: {accent_color} !important; }}
            .section-title {{ border-bottom-color: {accent_color} !important; border-left-color: {accent_color} !important; }}
            .skill-pill, .skill-tag, .skill-item {{ background: {accent_color}22 !important; color: {accent_color} !important; border-color: {accent_color} !important; }}
            """
        if font_family:
            override_style += f"""
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Roboto+Mono:wght@400;700&family=Lora:wght@400;700&family=Outfit:wght@400;700&display=swap');
            body, p, span, div, h1, h2, h3, li, a {{ font-family: {font_family}, 'Inter', sans-serif !important; }}
            """
        override_style += "</style>"
        html_content = html_content.replace("</head>", f"{override_style}\n</head>")

        tmp_dir  = tempfile.mkdtemp()
        pdf_path = os.path.join(tmp_dir, f"resume_{req.user_id[:8]}.pdf")

        pdf = weasyprint.HTML(string=html_content).write_pdf()
        with open(pdf_path, "wb") as f:
            f.write(pdf)

        _increment_download_limit(req.user_id, req.is_pro)

        return FileResponse(
            path        = pdf_path,
            media_type  = "application/pdf",
            filename    = f"{req.json_resume.basics.name.replace(' ', '_') or 'Resume'}.pdf",
        )

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PDF generation not available on this server. Please install weasyprint."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
