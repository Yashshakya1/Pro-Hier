from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict, List
import os
from dotenv import load_dotenv

load_dotenv()

# ── State ──────────────────────────────────────────
class InternshipState(TypedDict):
    resume_text: str
    field: str              # "AI/ML", "Web Dev", etc
    user_type: str          # "Student", "Fresher"
    location: str           # User's target location
    profile_summary: str
    internships: List[dict]
    best_match: dict
    application_tips: str
    application_tips: str

# ── LLM ───────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Node 1 — Analyze Profile ──────────────────────
def analyze_profile(state: InternshipState) -> InternshipState:
    prompt = f"""
    Analyze this candidate profile for internship matching.
    
    Resume: {state["resume_text"]}
    Field: {state["field"]}
    User Type: {state["user_type"]}
    
    Return a Python dictionary:
    {{
        "summary": "2 line profile summary",
        "strong_skills": ["skill1", "skill2"],
        "level": "Beginner/Intermediate/Advanced"
    }}
    Return ONLY the dictionary. No explanation.
    """
    response = llm.invoke(prompt)
    try:
        result = eval(response.content.strip())
        summary = result.get("summary", "")
    except:
        summary = "Strong candidate with relevant skills"
    
    return {**state, "profile_summary": summary}

# ── Helper ──────────────────────────────────────────
from utils.internship_scraper import scrape_live_internships

# ── Node 2 — Find Internships ─────────────────────
def find_internships(state: InternshipState) -> InternshipState:
    # 1. SCRAPE REAL LISTINGS FIRST
    location = state.get("location", "")
    real_internships = scrape_live_internships(state["field"], location)
    
    if not real_internships:
        # Fallback if scraper fails
        prompt = f"""
        Suggest 5 real internship opportunities for this candidate. Do NOT invent stipends (use 'Standard').
        Give actual general search links for the 'link' property.
        
        Field: {state["field"]}
        Location: {location}
        Profile: {state["profile_summary"]}
        
        Return a Python list of 5 dictionaries:
        [{{ "company": "...", "role": "...", "duration": "...", "stipend": "Standard", "platform": "LinkedIn", "match_score": 85, "link": "https://..." }}]
        Return ONLY the list. No explanation.
        """
    else:
        # USE REAL DATA TO PREVENT HALLUCINATIONS
        prompt = f"""
        Here is a list of REAL LIVE internship postings from the web right now:
        {real_internships}
        
        Candidate Profile: {state["profile_summary"]}
        
        Filter and select the top 5 most relevant internships from the real list provided above for the candidate.
        Calculate a 'match_score' (out of 100) for each.
        You MUST keep the exact same 'company', 'role', 'stipend', 'duration', 'platform', and 'link' as the real postings. DO NOT MODIFY THE LINKS OR DETAILS.
        
        Return a Python list of dictionaries:
        [{{ "company": "...", "role": "...", "duration": "...", "stipend": "...", "platform": "Internshala", "match_score": 85, "link": "https://..." }}]
        Return ONLY the Python list. No explanation.
        """
        
    response = llm.invoke(prompt)
    try:
        internships = eval(response.content.strip())
        if not isinstance(internships, list):
            internships = real_internships[:5] if real_internships else []
    except:
        internships = real_internships[:5] if real_internships else []
    
    return {**state, "internships": internships}

# ── Node 3 — Find Best Match ──────────────────────
def find_best_match(state: InternshipState) -> InternshipState:
    if not state["internships"]:
        return {**state, "best_match": {}}
    
    # Sort by match score
    sorted_internships = sorted(
        state["internships"],
        key=lambda x: x.get("match_score", 0),
        reverse=True
    )
    best = sorted_internships[0]
    return {**state, "best_match": best}

# ── Node 4 — Application Tips ─────────────────────
def generate_tips(state: InternshipState) -> InternshipState:
    prompt = f"""
    Give 3 specific application tips for this internship.
    
    Best Match: {state["best_match"]}
    Candidate Profile: {state["profile_summary"]}
    Field: {state["field"]}
    
    Return 3 actionable, specific tips.
    Be concise and practical.
    """
    response = llm.invoke(prompt)
    return {**state, "application_tips": response.content}

# ── Build Graph ───────────────────────────────────
def build_internship_agent():
    graph = StateGraph(InternshipState)
    
    graph.add_node("analyze_profile", analyze_profile)
    graph.add_node("find_internships", find_internships)
    graph.add_node("find_best_match", find_best_match)
    graph.add_node("generate_tips", generate_tips)
    
    graph.set_entry_point("analyze_profile")
    graph.add_edge("analyze_profile", "find_internships")
    graph.add_edge("find_internships", "find_best_match")
    graph.add_edge("find_best_match", "generate_tips")
    graph.add_edge("generate_tips", END)
    
    return graph.compile()

internship_agent = build_internship_agent()