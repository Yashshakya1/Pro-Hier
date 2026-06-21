"""
Resume Builder AI Agent — ProHire AI
Uses existing llm (Cerebras → Groq fallback) to enhance resume content.
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from utils.llm_client import llm


# ── State ──────────────────────────────────────────────────────────────
class BuilderState(TypedDict):
    summary: str
    experience: list          # list of dicts: {title, company, duration, bullets}
    skills: list              # list of strings
    is_pro: bool
    job_title: str            # target role for context

    # outputs
    enhanced_summary: str
    enhanced_experience: list
    suggested_skills: list
    error: Optional[str]


# ── Node 1: Enhance Professional Summary ──────────────────────────────
def enhance_summary(state: BuilderState) -> BuilderState:
    try:
        prompt = f"""You are an expert resume writer. Rewrite this professional summary to be:
- More impactful, concise, and ATS-optimized
- Tailored for the role: {state['job_title']}
- Max 3 sentences, use action-oriented language
- Do NOT add fake achievements. Only improve wording.

Original Summary:
{state['summary'] or 'No summary provided, write a generic professional one based on the role.'}

Return ONLY the improved summary text. No quotes, no labels."""

        response = llm.invoke(prompt)
        return {**state, "enhanced_summary": response.content.strip()}
    except Exception as e:
        return {**state, "enhanced_summary": state.get("summary", ""), "error": str(e)}


# ── Node 2: Enhance Experience Bullets ───────────────────────────────
def enhance_experience(state: BuilderState) -> BuilderState:
    try:
        if not state.get("experience"):
            return {**state, "enhanced_experience": []}

        enhanced_list = []
        for exp in state["experience"]:
            bullets_text = "\n".join(f"- {b}" for b in (exp.get("bullets") or []))
            if not bullets_text:
                enhanced_list.append(exp)
                continue

            prompt = f"""You are an expert resume writer. Improve these job experience bullet points for:
Role: {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}
Target Role: {state['job_title']}

Rules:
- Start each bullet with a strong action verb (Developed, Led, Optimized, etc.)
- Add quantified results where possible (e.g., "by 30%", "for 50+ users")
- Keep each bullet under 20 words
- Maintain the SAME number of bullets

Original bullets:
{bullets_text}

Return ONLY the improved bullets as a Python list of strings. Example: ["Built X...", "Led Y..."]
No explanation, no code block."""

            response = llm.invoke(prompt)
            try:
                improved = eval(response.content.strip())
                if not isinstance(improved, list):
                    improved = exp.get("bullets", [])
            except Exception:
                improved = exp.get("bullets", [])

            enhanced_list.append({**exp, "bullets": improved})

        return {**state, "enhanced_experience": enhanced_list}
    except Exception as e:
        return {**state, "enhanced_experience": state.get("experience", []), "error": str(e)}


# ── Node 3: Suggest Additional Skills (Pro only) ──────────────────────
def suggest_skills(state: BuilderState) -> BuilderState:
    if not state.get("is_pro"):
        return {**state, "suggested_skills": []}

    try:
        existing = ", ".join(state.get("skills") or [])
        prompt = f"""You are a career coach. Based on the target role "{state['job_title']}", suggest 5-8 additional skills that:
- Are NOT already in the user's existing skills list
- Are high-demand and ATS-relevant for this role
- Are specific (not generic like "Communication")

Existing skills: {existing or 'None listed'}

Return ONLY a Python list of strings. Example: ["Docker", "System Design", "AWS Lambda"]
No explanation."""

        response = llm.invoke(prompt)
        try:
            suggestions = eval(response.content.strip())
            if not isinstance(suggestions, list):
                suggestions = []
        except Exception:
            suggestions = []

        return {**state, "suggested_skills": suggestions}
    except Exception as e:
        return {**state, "suggested_skills": [], "error": str(e)}


# ── Build LangGraph ───────────────────────────────────────────────────
def build_resume_builder_agent():
    graph = StateGraph(BuilderState)

    graph.add_node("enhance_summary",    enhance_summary)
    graph.add_node("enhance_experience", enhance_experience)
    graph.add_node("suggest_skills",     suggest_skills)

    graph.set_entry_point("enhance_summary")
    graph.add_edge("enhance_summary",    "enhance_experience")
    graph.add_edge("enhance_experience", "suggest_skills")
    graph.add_edge("suggest_skills",     END)

    return graph.compile()


resume_builder_agent = build_resume_builder_agent()
