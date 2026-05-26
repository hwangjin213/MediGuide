import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    print("Initializing GenAI Client...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    print("Fetching models list...")
    # List available models
    models = client.models.list()
    print("\n--- Supported Models for your API Key ---")
    for m in models:
        # Print only model name and supported actions
        print(f"- {m.name} (Supported: {m.supported_actions})")
        
except Exception as e:
    print(f"\n❌ Failed to list models: {e}")
