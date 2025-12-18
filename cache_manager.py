import os
import hashlib
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) # REMOVED global init

MODEL_ID = 'gemini-3-flash-preview'

# Singleton Client
_client_instance = None

def get_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client_instance

def get_cache_version(text):
    """Creates a unique hash for the prompt text."""
    return hashlib.md5(text.encode()).hexdigest()[:8]

def get_active_cache(display_name):
    try:
        client = get_client()
        for c in client.caches.list():
            if c.display_name == display_name:
                return c.name
        return None
    except Exception as e:
        print(f"[CACHE] Error listing: {e}")
        return None

def create_cache(content_text, tools_list, display_name):
    try:
        client = get_client()
        # PADDING LOGIC
        # Caching requires min 2048 tokens. If we are under, we pad.
        # Check count first
        try:
             count_resp = client.models.count_tokens(model=MODEL_ID, contents=content_text)
             token_count = count_resp.total_tokens
             print(f"[CACHE] System Prompt Tokens: {token_count}")
             
             if token_count < 2100:
                 # Calculate deficit
                 needed = 2200 - token_count # Aim for 2200 to be safe
                 print(f"[CACHE] Padding with ~{needed} tokens to meet requirements...")
                 # 1 token is roughly 4 chars, but " a " is 1 token.
                 padding = " a " * needed 
                 content_text += f"\n\n<system_padding_ignore_this>\n{padding}\n</system_padding_ignore_this>"
        except Exception as e:
            print(f"[CACHE] Padding Check Failed (skipping padding): {e}")

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
