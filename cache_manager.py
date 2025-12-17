import os
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Cache Configuration
CACHE_TTL_MINUTES = 60 # Caches expire if not used. 
MODEL_ID = 'gemini-2.5-pro'

def get_active_cache(display_name="RoleplayBot_Rules"):
    """
    Checks if a valid cache exists with the given name.
    """
    try:
        # List caches (SDK specific syntax)
        for c in client.caches.list():
            if c.display_name == display_name:
                # Check expiration
                # SDK might handle this, but for now assuming if it lists, it's valid.
                return c.name
        return None
    except Exception as e:
        print(f"[CACHE] Error listing caches: {e}")
        return None

def create_cache(content_text, display_name="RoleplayBot_Rules"):
    """
    Creates a new context cache with the static system instructions.
    """
    try:
        # Create cache config
        # Note: TTL is usually set via expire_time or ttl duration.
        # Checking SDK docs via implementation...
        
        # NOTE: 2.5 SDK syntax might vary. Using standard google.genai pattern.
        cache = client.caches.create(
            model=MODEL_ID,
            config=types.CreateCachedContentConfig(
                display_name=display_name,
                system_instruction=types.Part(text=content_text),
                contents=[], # No user history in the cache, just system prompt
                ttl="3600s" # 1 Hour TTL
            )
        )
        print(f"[CACHE] Created new cache: {cache.name}")
        return cache.name
    except Exception as e:
        print(f"[CACHE] Creation failed: {e}")
        return None

def get_or_create_cache(system_text):
    """
    Orchestrator to get active or create new cache.
    """
    existing_name = get_active_cache()
    if existing_name:
        print(f"[CACHE] Using existing cache: {existing_name}")
        return existing_name
    
    return create_cache(system_text)
