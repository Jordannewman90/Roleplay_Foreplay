import asyncio
import functools
import random
from google.api_core import exceptions
import google.genai

def retry_with_backoff(retries=3, initial_delay=2, factor=2):
    """
    Decorator to retry async functions on ResourceExhausted (429) errors.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # In google-genai, the error structure might vary, but we look for 429
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or isinstance(e, exceptions.ResourceExhausted):
                        if i == retries - 1:
                            raise e # Give up on last try
                        
                        jitter = random.uniform(0, 1)
                        wait_time = delay + jitter
                        print(f"⚠️ Rate Limit (429). Retrying in {wait_time:.2f}s... ({i+1}/{retries})")
                        await asyncio.sleep(wait_time)
                        delay *= factor
                    else:
                        raise e # Re-raise non-429 errors
            return None # Should not be reached
        return wrapper
    return decorator
