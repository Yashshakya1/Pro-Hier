import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Ensure environment variables are loaded
load_dotenv()

def get_llm():
    cerebras_api_key = os.getenv("CEREBRAS_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    # Check if Cerebras API Key is configured and not empty
    if cerebras_api_key and cerebras_api_key.strip():
        model_name = os.getenv("CEREBRAS_MODEL", "llama3.1-8b").strip()
        print(f"🔌 [LLM] Using Cerebras Inference API (Model: {model_name})")
        try:
            from langchain_cerebras import ChatCerebras
            return ChatCerebras(
                model=model_name,
                api_key=cerebras_api_key,
                temperature=0.1
            )
        except Exception as e:
            print(f"⚠️ [LLM] Failed to load langchain-cerebras. Falling back to Groq. Error: {e}")
            
    # Fallback to Groq if Cerebras key is missing or failed
    fallback_model = "llama-3.3-70b-versatile"
    print(f"🔌 [LLM] Using Fallback Groq API (Model: {fallback_model})")
    return ChatGroq(
        model=fallback_model,
        api_key=groq_api_key
    )

# Export the singleton-like instance for all agents to share
llm = get_llm()
