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
    location = state.get("location", "")
    role = state["field"]
    
    # 1. SCRAPE REAL LISTINGS FIRST
    real_internships = scrape_live_internships(role, location)
    
    # 2. INSTRUCT LLM TO COMBINE REAL POSTINGS + 15 PLATFORM DEEP LINKS
    prompt = f"""
    The user strictly requested to see jobs ONLY from the last 3 days across EXACTLY these platforms:
    LinkedIn, Indeed, Glassdoor, Handshake, Internshala, LetsIntern, Twenty19, HelloIntern, Freshersworld, Idealist, Naukri, Firstnaukri, Qureos, Company Career Pages, University Career Portals.
    
    Natively scraped LIVE postings (already filtered < 3 days):
    {real_internships}
    
    Candidate Profile: {state["profile_summary"]}
    Role: {role}
    Location: {location}
    
    INSTRUCTIONS (STRICT):
    1. You MUST include ALL the REAL LIVE postings from the scraped data above EXACTLY as they are at the very beginning of the list. Guarantee a high integer 'match_score' (e.g. 95) for them.
    2. For ALL the other platforms in the list above, you MUST create a custom "Portal Card".
       - "company": "[Platform Name] Deep Link Portal"
       - "role": "Tap Here to Browse {role} Matches"
       - "duration": "Live Search"
       - "stipend": "Check Portal"
       - "platform": "[Platform Name]"
       - "match_score": 90
       - "link": A functionally correct Deep Link Search URL restricted to the LAST 3 DAYS (e.g., Indeed uses '&fromage=3'). MUST start with https://
    3. You must output exactly 15-20 dictionaries total (real ones + portal cards) so the user sees every requested platform on their screen.
    
    Return ONLY a highly valid JSON array of objects. Do not use Python `None` or formatting like ```json.
    [{{ "company": "...", "role": "...", "duration": "...", "stipend": "...", "platform": "Internshala", "match_score": 85, "link": "https://..." }}]
    """
        
    response = llm.invoke(prompt)
    try:
        import json
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        internships = json.loads(content)
        if not isinstance(internships, list):
            internships = real_internships[:5] if real_internships else []
            
        # Sanitize URLs to prevent 400 Bad Request if LLM generated spaces in deep links
        for job in internships:
            if "link" in job and isinstance(job["link"], str):
                job["link"] = job["link"].replace(" ", "%20")
    except Exception as e:
        print(f"JSON Parse Error: {{e}}")
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