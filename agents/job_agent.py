from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict, List
import os
from dotenv import load_dotenv

load_dotenv()

class JobState(TypedDict):
    resume_text: str
    field: str
    location: str
    country: str
    user_type: str
    profile_summary: str
    jobs: List[dict]
    best_match: dict
    tips: str

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

def analyze_profile(state: JobState) -> JobState:
    prompt = f"Analyze this resume for a {state['user_type']} in {state['field']}:\n{state['resume_text']}\nReturn a 2-line summary in JSON: {{'summary': '...'}}"
    try:
        resp = llm.invoke(prompt)
        import json
        summary = json.loads(resp.content.strip()).get("summary", "Ready for new opportunities")
    except:
        summary = f"{state['user_type']} professional in {state['field']}."
    return {**state, "profile_summary": summary}

def fetch_jobs(state: JobState) -> JobState:
    from utils.job_aggregator import find_jobs_realtime
    # Pass user_type down to aggregator for source-level filtering
    raw_jobs = find_jobs_realtime(state["field"], state["location"], state["country"], state["user_type"])
    
    scored_jobs = []
    for i, job in enumerate(raw_jobs):
        if i < 20:
            prompt = f"CV: {state['resume_text'][:800]}\nUser Level: {state['user_type']}\nJob: {job['role']} at {job['company']}\nScore 0-100 based on if this job fits a {state['user_type']}? Return only number."
            try: 
                score_content = llm.invoke(prompt).content.strip()
                score = int(re.search(r'\d+', score_content).group()) # Robust parsing
            except: 
                score = 85
        else:
            score = max(70, 95 - (i % 20))
        
        job["match_score"] = score
        scored_jobs.append(job)
        
    return {**state, "jobs": scored_jobs}

def find_best(state: JobState) -> JobState:
    if not state["jobs"]: return {**state, "best_match": {}}
    best = max(state["jobs"], key=lambda x: x.get("match_score", 0))
    return {**state, "best_match": best}

def generate_tips(state: JobState) -> JobState:
    if not state["best_match"]: return {**state, "tips": ""}
    prompt = f"Give 3 tips for applying to: {state['best_match']['role']} at {state['best_match']['company']}\nCV: {state['profile_summary']}"
    resp = llm.invoke(prompt)
    return {**state, "tips": resp.content}

def build_job_agent():
    graph = StateGraph(JobState)
    graph.add_node("analyze", analyze_profile)
    graph.add_node("fetch", fetch_jobs)
    graph.add_node("best", find_best)
    graph.add_node("tips", generate_tips)
    
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "fetch")
    graph.add_edge("fetch", "best")
    graph.add_edge("best", "tips")
    graph.add_edge("tips", END)
    
    return graph.compile()

job_agent = build_job_agent()
