import os
import sys

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.llm_client import get_llm

def test_llm_fallback():
    print("\n--- Test 1: Fallback Mode (Groq) ---")
    # Backup existing keys
    old_cerebras_key = os.environ.get("CEREBRAS_API_KEY")
    if "CEREBRAS_API_KEY" in os.environ:
        del os.environ["CEREBRAS_API_KEY"]
        
    print("Testing get_llm() when CEREBRAS_API_KEY is not set...")
    llm = get_llm()
    print(f"Instantiated model instance: {type(llm).__name__}")
    
    # Try a simple invocation
    try:
        response = llm.invoke("Hello, say 'Groq is ready' in 3 words.")
        print(f"Response: {response.content.strip()}")
        print("✅ Fallback Test Passed!")
    except Exception as e:
        print(f"❌ Fallback Test Failed: {e}")
        
    # Restore key if backed up
    if old_cerebras_key is not None:
        os.environ["CEREBRAS_API_KEY"] = old_cerebras_key

def test_llm_cerebras():
    print("\n--- Test 2: Cerebras Mode (if key provided) ---")
    cerebras_key = os.environ.get("CEREBRAS_API_KEY")
    if not cerebras_key or not cerebras_key.strip():
        # Check from dotenv as well
        from dotenv import load_dotenv
        load_dotenv()
        cerebras_key = os.getenv("CEREBRAS_API_KEY")
        
    if not cerebras_key or not cerebras_key.strip():
        print("⏭️ Skipping Cerebras Test (CEREBRAS_API_KEY is not configured in .env or shell).")
        return
        
    print("Testing get_llm() with active CEREBRAS_API_KEY...")
    llm = get_llm()
    print(f"Instantiated model instance: {type(llm).__name__}")
    
    try:
        response = llm.invoke("Hello, say 'Cerebras is ready' in 3 words.")
        print(f"Response: {response.content.strip()}")
        print("✅ Cerebras Test Passed!")
    except Exception as e:
        print(f"❌ Cerebras Test Failed: {e}")

if __name__ == "__main__":
    test_llm_fallback()
    test_llm_cerebras()
