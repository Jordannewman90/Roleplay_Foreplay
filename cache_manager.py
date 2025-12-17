import os
import hashlib
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_ID = 'gemini-2.5-pro'

def get_cache_version(text):
    """Creates a unique hash for the prompt text."""
    return hashlib.md5(text.encode()).hexdigest()[:8]

def get_active_cache(display_name):
    try:
        for c in client.caches.list():
            if c.display_name == display_name:
                return c.name
        return None
    except Exception as e:
        print(f"[CACHE] Error listing: {e}")
        return None

def create_cache(content_text, tools_list, display_name):
    try:
        # We include tools in the cache creation for better performance
        cache = client.caches.create(
            model=MODEL_ID,
            config=types.CreateCachedContentConfig(
                display_name=display_name,
                system_instruction=types.Part(text=content_text),
                tools=tools_list, 
                ttl="3600s" 
            )
        )
        print(f"[CACHE] Created: {display_name}")
        return cache.name
    except Exception as e:
        print(f"[CACHE] Creation failed: {e}")
        return None

def get_or_create_cache(system_text, tools_list):
    # Unique name based on the prompt content
    version = get_cache_version(system_text)
    full_display_name = f"DM_Cache_v_{version}"
    
    existing_name = get_active_cache(full_display_name)
    if existing_name:
        return existing_name
    
    return create_cache(system_text, tools_list, full_display_name)
