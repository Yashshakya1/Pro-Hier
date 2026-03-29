from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict, List
import os
from dotenv import load_dotenv

load_dotenv()

# ── State ──────────────────────────────────────────
class InterviewState(TypedDict):
    resume_text: str
    job_role: str
    interview_type: str      # "HR" or "Technical"
    questions: List[str]
    current_question: str
    user_answer: str
    evaluation: str
    followup_question: str
    final_score: int
    final_feedback: str

# ── LLM ───────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Node 1 — Analyze Profile ──────────────────────
def analyze_profile(state: InterviewState) -> InterviewState:
    prompt = f"""
    You are an expert interviewer.
    Candidate's Resume: {state["resume_text"]}
    Job Role: {state["job_role"]}
    Interview Type: {state["interview_type"]}
    
    Generate 5 relevant interview questions.
    Return ONLY a Python list of 5 strings.
    No explanation, no numbering.
    """
    response = llm.invoke(prompt)
    try:
        questions = eval(response.content.strip())
        if not isinstance(questions, list):
            questions = []
    except:
        questions = [
            "Tell me about yourself.",
            "What are your strengths?",
            "Why do you want this role?",
            "Where do you see yourself in 5 years?",
            "Do you have any questions for us?"
        ]
    
    current = questions[0] if questions else "Tell me about yourself."
    return {**state, "questions": questions, "current_question": current}

# ── Node 2 — Generate Question ────────────────────
def generate_question(state: InterviewState) -> InterviewState:
    # Already generated in analyze_profile
    # This node formats the question nicely
    prompt = f"""
    Rephrase this interview question to sound natural and conversational:
    "{state["current_question"]}"
    
    Return ONLY the rephrased question. Nothing else.
    """
    response = llm.invoke(prompt)
    return {**state, "current_question": response.content.strip()}

# ── Node 3 — Evaluate Answer ──────────────────────
def evaluate_answer(state: InterviewState) -> InterviewState:
    prompt = f"""
    You are an expert interviewer evaluating a candidate's answer.
    
    Job Role: {state["job_role"]}
    Question: {state["current_question"]}
    Candidate's Answer: {state["user_answer"]}
    
    Evaluate the answer and provide:
    1. Score out of 10
    2. What was good
    3. What was missing
    4. Better sample answer
    
    Be constructive and encouraging.
    """
    response = llm.invoke(prompt)
    return {**state, "evaluation": response.content}

# ── Node 4 — Generate Followup ────────────────────
def generate_followup(state: InterviewState) -> InterviewState:
    prompt = f"""
    Based on this interview answer, generate ONE smart follow-up question.
    
    Original Question: {state["current_question"]}
    Candidate's Answer: {state["user_answer"]}
    
    Return ONLY the follow-up question. Nothing else.
    """
    response = llm.invoke(prompt)
    return {**state, "followup_question": response.content.strip()}

# ── Node 5 — Final Score ──────────────────────────
def calculate_final_score(state: InterviewState) -> InterviewState:
    prompt = f"""
    Based on this interview evaluation, give:
    1. Final score out of 100
    2. Overall performance summary (2-3 lines)
    3. Top 3 areas to improve
    
    Evaluation: {state["evaluation"]}
    Job Role: {state["job_role"]}
    
    Format:
    SCORE: [number]
    SUMMARY: [text]
    IMPROVEMENTS: [3 bullet points]
    """
    response = llm.invoke(prompt)
    
    # Extract score
    try:
        lines = response.content.split("\n")
        score_line = [l for l in lines if "SCORE:" in l][0]
        score = int(''.join(filter(str.isdigit, score_line)))
        score = min(100, max(0, score))
    except:
        score = 70
    
    return {**state, "final_score": score, "final_feedback": response.content}

# ── Build Graph ───────────────────────────────────
def build_interview_agent():
    graph = StateGraph(InterviewState)
    
    graph.add_node("analyze_profile", analyze_profile)
    graph.add_node("generate_question", generate_question)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("generate_followup", generate_followup)
    graph.add_node("calculate_final_score", calculate_final_score)
    
    graph.set_entry_point("analyze_profile")
    graph.add_edge("analyze_profile", "generate_question")
    graph.add_edge("generate_question", "evaluate_answer")
    graph.add_edge("evaluate_answer", "generate_followup")
    graph.add_edge("generate_followup", "calculate_final_score")
    graph.add_edge("calculate_final_score", END)
    
    return graph.compile()

interview_agent = build_interview_agent()