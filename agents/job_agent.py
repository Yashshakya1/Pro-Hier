from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict, List
import os
import re
import json
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
    boost_keywords: List[str]

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
    if not state["best_match"]: return {**state, "tips": "", "boost_keywords": []}
    
    prompt = f"""
    Analyze the gap between this CV and the Job.
    CV Summary: {state['profile_summary']}
    Job: {state['best_match']['role']} at {state['best_match']['company']}
    
    Return exactly 2 parts in JSON:
    1. "tips": "3 short application tips"
    2. "boost_keywords": ["Exactly 3 missing skills/keywords to add to CV to reach 98% match"]
    """
    
    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        # Robust JSON Extraction
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = json.loads(content)
            
        return {
            **state, 
            "tips": data.get("tips", "Apply with confidence!"),
            "boost_keywords": data.get("boost_keywords", [])[:3]
        }
    except Exception as e:
        print(f"Job Tips Error: {e}")
        return {**state, "tips": "Customize your resume for this role.", "boost_keywords": ["Relevant Tech Stack", "Industry Experience", "Soft Skills"]}

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
