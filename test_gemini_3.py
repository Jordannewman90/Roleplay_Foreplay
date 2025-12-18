import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv()

async def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return

    print(f"Found API Key: {api_key[:5]}...{api_key[-4:]}")
    
    client = genai.Client(api_key=api_key)
    model_id = 'gemini-3-flash-preview'
    
    try:
        print(f"Pinging {model_id}...")
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_id,
            contents="Hello! Are you Gemini 3?"
        )
        print(f"SUCCESS! Response received:")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"CONNECTION FAILED:")
        print(e)

if __name__ == "__main__":
    asyncio.run(test_gemini())
