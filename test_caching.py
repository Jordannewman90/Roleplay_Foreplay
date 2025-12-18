import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    # Attempt to list caches or check attribute
    print("Checking client.caches...")
    if hasattr(client, 'caches'):
        print("Success: client.caches exists.")
        # Try to create a dummy cache? No, just existence check is enough for now.
    else:
        print("Failure: client.caches does NOT exist.")

except Exception as e:
    print(f"Error checking caches: {e}")
