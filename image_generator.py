import os
import io
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Client
# LAZY LOADING: Moved inside functions to prevent startup crashes if key is missing.
IMAGE_MODEL_ID = 'gemini-2.5-flash-image'

def get_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_scene_image(prompt):
    """
    Generates an image based on a text prompt.
    Returns: (image_bytes, file_extension_str) or (None, error_message)
    """
    try:
        client = get_client()
        response = client.models.generate_content(
            model=IMAGE_MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7 
            )
        )
        
        if response.parts:
            for part in response.parts:
                if part.inline_data:
                    return part.inline_data.data, "jpg" # Defaulting to jpg as requested in config
                    
        return None, "No image data returned from API."

    except Exception as e:
        return None, str(e)

def generate_avatar(instruction, input_image_bytes=None, input_mime_type=None):
    """
    Generates an avatar, optionally using a reference image.
    Returns: (image_bytes, file_extension_str) or (None, error_message)
    """
    try:
        client = get_client()
        contents = [types.Part(text=instruction)]
        
        if input_image_bytes and input_mime_type:
             contents.append(types.Part.from_bytes(input_image_bytes, input_mime_type))

        response = client.models.generate_content(
            model=IMAGE_MODEL_ID,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7
            )
        )

        if response.parts:
            for part in response.parts:
                if part.inline_data:
                    return part.inline_data.data, "jpg"

        return None, "No image data returned from API."

    except Exception as e:
        return None, str(e)
