from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict
from utils.pdf_parser import extract_text_from_pdf
import os
from dotenv import load_dotenv

load_dotenv()

# ── State ──────────────────────────────────────────
class ResumeState(TypedDict):
    pdf_path: str
    jd_text: str
    resume_text: str
    skills: list
    jd_keywords: list
    ats_score: int
    feedback: str

# ── LLM ───────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Node 1 ────────────────────────────────────────
def parse_resume(state: ResumeState) -> ResumeState:
    text = extract_text_from_pdf(state["pdf_path"])
    return {**state, "resume_text": text}

# ── Node 2 ────────────────────────────────────────
def extract_skills(state: ResumeState) -> ResumeState:
    prompt = f"""
    Extract all technical and soft skills from this resume.
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
    return {**state, "skills": skills}

# ── Node 3 ────────────────────────────────────────
def parse_jd(state: ResumeState) -> ResumeState:
    prompt = f"""
    Extract all required skills and keywords from this Job Description.
    Return ONLY a Python list of strings. No explanation.
    JD: {state["jd_text"]}
    """
    response = llm.invoke(prompt)
    try:
        keywords = eval(response.content.strip())
        if not isinstance(keywords, list):
            keywords = []
    except:
        keywords = []
    return {**state, "jd_keywords": keywords}

# ── Node 4 ────────────────────────────────────────
def ats_score_calculator(state: ResumeState) -> ResumeState:
    skills = [s.lower() for s in state["skills"]]
    keywords = [k.lower() for k in state["jd_keywords"]]
    if not keywords:
        return {**state, "ats_score": 0}
    matched = sum(1 for k in keywords if k in skills)
    score = int((matched / len(keywords)) * 100)
    return {**state, "ats_score": score}

# ── Node 5 ────────────────────────────────────────
def feedback_generator(state: ResumeState) -> ResumeState:
    prompt = f"""
    You are a professional resume coach.
    Resume Skills: {state["skills"]}
    JD Keywords: {state["jd_keywords"]}
    ATS Score: {state["ats_score"]}/100
    
    Give structured feedback:
    1. ✅ Matched Skills
    2. ❌ Missing Skills
    3. 💡 3 Actionable Tips
    Be concise and helpful.
    """
    response = llm.invoke(prompt)
    return {**state, "feedback": response.content}

# ── Build Graph ───────────────────────────────────
def build_resume_agent():
    graph = StateGraph(ResumeState)
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("extract_skills", extract_skills)
    graph.add_node("parse_jd", parse_jd)
    graph.add_node("ats_score_calculator", ats_score_calculator)
    graph.add_node("feedback_generator", feedback_generator)
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "extract_skills")
    graph.add_edge("extract_skills", "parse_jd")
    graph.add_edge("parse_jd", "ats_score_calculator")
    graph.add_edge("ats_score_calculator", "feedback_generator")
    graph.add_edge("feedback_generator", END)
    return graph.compile()

resume_agent = build_resume_agent()