from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict, List
import os
from dotenv import load_dotenv

load_dotenv()

# ── State ──────────────────────────────────────────
class SkillGapState(TypedDict):
    resume_text: str
    jd_text: str
    resume_skills: List[str]
    required_skills: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    resources: dict
    gap_score: int

# ── LLM ───────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Node 1 — Extract Resume Skills ───────────────
def extract_resume_skills(state: SkillGapState) -> SkillGapState:
    prompt = f"""
    Extract all technical skills from this resume.
    Return ONLY a Python list of strings. No explanation.
    Resume: {state["resume_text"]}
    """
    response = llm.invoke(prompt)
    try:
        skills = eval(response.content.strip())
        if not isinstance(skills, list):
            skills = []
    except:
        skills = []
    return {**state, "resume_skills": skills}

# ── Node 2 — Extract JD Skills ────────────────────
def extract_jd_skills(state: SkillGapState) -> SkillGapState:
    prompt = f"""
    Extract all required skills from this Job Description.
    Return ONLY a Python list of strings. No explanation.
    JD: {state["jd_text"]}
    """
    response = llm.invoke(prompt)
    try:
        skills = eval(response.content.strip())
        if not isinstance(skills, list):
            skills = []
    except:
        skills = []
    return {**state, "required_skills": skills}

# ── Node 3 — Find Gap ─────────────────────────────
def find_gap(state: SkillGapState) -> SkillGapState:
    resume = [s.lower() for s in state["resume_skills"]]
    required = [s.lower() for s in state["required_skills"]]
    
    matched = [s for s in required if s in resume]
    missing = [s for s in required if s not in resume]
    
    score = int((len(matched) / len(required)) * 100) if required else 0
    
    return {
        **state,
        "matched_skills": matched,
        "missing_skills": missing,
        "gap_score": score
    }

# ── Node 4 — Suggest Resources ────────────────────
def suggest_resources(state: SkillGapState) -> SkillGapState:
    prompt = f"""
    For each missing skill, suggest the best FREE learning resource.
    Missing skills: {state["missing_skills"]}
    
    Return a Python dictionary like:
    {{"skill_name": "resource_url_or_name", ...}}
    
    Use YouTube, freeCodeCamp, or official docs.
    Return ONLY the dictionary. No explanation.
    """
    response = llm.invoke(prompt)
    try:
        resources = eval(response.content.strip())
        if not isinstance(resources, dict):
            resources = {}
    except:
        resources = {}
    return {**state, "resources": resources}

# ── Build Graph ───────────────────────────────────
def build_skill_gap_agent():
    graph = StateGraph(SkillGapState)
    
    graph.add_node("extract_resume_skills", extract_resume_skills)
    graph.add_node("extract_jd_skills", extract_jd_skills)
    graph.add_node("find_gap", find_gap)
    graph.add_node("suggest_resources", suggest_resources)
    
    graph.set_entry_point("extract_resume_skills")
    graph.add_edge("extract_resume_skills", "extract_jd_skills")
    graph.add_edge("extract_jd_skills", "find_gap")
    graph.add_edge("find_gap", "suggest_resources")
    graph.add_edge("suggest_resources", END)
    
    return graph.compile()

skill_gap_agent = build_skill_gap_agent()