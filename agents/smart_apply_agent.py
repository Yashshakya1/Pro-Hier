from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict, List
import os
from dotenv import load_dotenv

load_dotenv()

# ── State ──────────────────────────────────────────
class SmartApplyState(TypedDict):
    resume_text: str
    job_title: str
    company_name: str
    jd_text: str
    match_score: int
    match_reasons: List[str]
    cover_letter: str
    application_status: str

# ── LLM ───────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Node 1 — Analyze Match ────────────────────────
def analyze_match(state: SmartApplyState) -> SmartApplyState:
    prompt = f"""
    Compare this resume with the job description.
    
    Resume: {state["resume_text"]}
    Job Title: {state["job_title"]}
    Company: {state["company_name"]}
    JD: {state["jd_text"]}
    
    Reply in this EXACT format, nothing else:
    SCORE: <number between 0-100>
    REASONS: <reason1> | <reason2> | <reason3>
    """
    response = llm.invoke(prompt)
    
    try:
        lines = response.content.strip().split("\n")
        score_line = [l for l in lines if "SCORE:" in l][0]
        reasons_line = [l for l in lines if "REASONS:" in l][0]
        
        score = int(''.join(filter(str.isdigit, score_line)))
        reasons = reasons_line.replace("REASONS:", "").strip().split("|")
        reasons = [r.strip() for r in reasons]
    except:
        score = 50
        reasons = ["Skills matched", "Experience relevant"]
    
    return {**state, "match_score": score, "match_reasons": reasons}

# ── Node 2 — Generate Cover Letter ───────────────
def generate_cover_letter(state: SmartApplyState) -> SmartApplyState:
    prompt = f"""
    Write a professional and personalized cover letter.
    
    Candidate Resume: {state["resume_text"]}
    Job Title: {state["job_title"]}
    Company: {state["company_name"]}
    Job Description: {state["jd_text"]}
    
    Cover letter should:
    - Be 3 paragraphs
    - Highlight matching skills
    - Show enthusiasm for the role
    - End with a call to action
    - Sound human and natural
    
    Return ONLY the cover letter text.
    """
    response = llm.invoke(prompt)
    return {**state, "cover_letter": response.content}

# ── Node 3 — Update Application Status ───────────
def update_status(state: SmartApplyState) -> SmartApplyState:
    status = "Applied ✅" if state["match_score"] >= 50 else "Low Match ⚠️"
    return {**state, "application_status": status}

# ── Build Graph ───────────────────────────────────
def build_smart_apply_agent():
    graph = StateGraph(SmartApplyState)
    
    graph.add_node("analyze_match", analyze_match)
    graph.add_node("generate_cover_letter", generate_cover_letter)
    graph.add_node("update_status", update_status)
    
    graph.set_entry_point("analyze_match")
    graph.add_edge("analyze_match", "generate_cover_letter")
    graph.add_edge("generate_cover_letter", "update_status")
    graph.add_edge("update_status", END)
    
    return graph.compile()

smart_apply_agent = build_smart_apply_agent()