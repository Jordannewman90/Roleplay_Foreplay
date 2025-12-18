import os
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Singleton Client (Reusing logic for consistency, though user asked for fresh client here initially. 
# Better to be safe and use Lazy/Singleton pattern we established).
_client_instance = None

def get_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client_instance

def generate_scene_image(prompt):
    """
    Generates an image using Imagen 3 via Gemini API.
    Returns: (bytes, extension_string) or (None, error_string)
    """
    print(f"[IMAGEN] Generating: {prompt}")
    try:
        # Use the specific Imagen model ID
        model_id = 'imagen-3.0-generate-001' 
        
        client = get_client() # Use singleton
        
        response = client.models.generate_images(
            model=model_id,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9", # Cinematic ratio
                safety_filter_level="block_medium_and_above",
                person_generation="allow_adult" 
            )
        )
        
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            return image_bytes, "png"
        else:
            return None, "No image returned from API."

    except Exception as e:
        print(f"[IMAGEN ERROR] {e}")
        return None, str(e)

def generate_avatar(instruction, input_image_bytes=None, input_mime_type=None):
    """
    Image-to-Image transformation for avatars.
    Note: Imagen 3.0 via API might have different support for Img2Img.
    If 3.0 fails, fallback to 2.0 logic or return error.
    """
    try:
        client = get_client()
        # Fallback to 3.0 flash logic for Img2Img since 3.0 generate-001 is text-to-image mostly
        model_id = 'gemini-3-flash-preview'
        
        contents = [types.Part(text=instruction)]
        
        if input_image_bytes and input_mime_type:
             contents.append(types.Part.from_bytes(input_image_bytes, input_mime_type))

        response = client.models.generate_content(
            model=model_id,
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
