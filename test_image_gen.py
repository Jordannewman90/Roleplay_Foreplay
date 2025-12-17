import os
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

def test_image_gen():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    print("--- Testing Image Generation (gemini-2.5-flash-image) ---")
    
    prompt = "Create a picture of a nano banana dish in a fancy restaurant with a Gemini theme"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
        )

        for part in response.parts:
            if part.text is not None:
                print(f"Text response: {part.text}")
            
            if part.inline_data is not None:
                # The SDK helper as_image() is very useful here
                try:
                    image = part.as_image()
                    image.save("test_generated_image.png")
                    print("SUCCESS! Saved test_generated_image.png")
                except Exception as e:
                    print(f"Error saving image: {e}")
                    # Fallback if as_image() isn't available in this specific version
                    # though user says it is.
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_image_gen()

if __name__ == "__main__":
    test_image_gen()
