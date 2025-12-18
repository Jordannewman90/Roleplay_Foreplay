import os
import wave
import io
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
# Initialize Client
# LAZY LOADING: Moved inside functions to prevent startup crashes.
SPEECH_MODEL_ID = 'gemini-2.5-flash-preview-tts'

# Singleton Client
_client_instance = None

def get_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client_instance

def generate_speech(text, voice_name='Kore'):
    """
    Generates speech audio from text using Gemini TTS.
    Returns: (wav_bytes, error_message)
    """
    if not text:
        return None, "Empty text provided."

    # Prevent potential API crashes on massive narrations
    safe_text = text[:3000] 

    try:
        client = get_client()
        response = client.models.generate_content(
            model=SPEECH_MODEL_ID,
            contents=[types.Part(text=safe_text)], # Wrapped for SDK consistency
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            )
        )
        
        # Verify response structure
        if not response.candidates or not response.candidates[0].content.parts:
            return None, "API returned successfully but contained no content."

        part = response.candidates[0].content.parts[0]
        
        if part.inline_data:
            pcm_data = part.inline_data.data
            
            # Convert PCM to WAV
            with io.BytesIO() as wav_io:
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2) 
                    wf.setframerate(24000)
                    wf.writeframes(pcm_data)
                
                return wav_io.getvalue(), None
                    
        return None, "No inline_data (audio) found in the response parts."

    except Exception as e:
        print(f"[TTS ERROR] {e}") # Log it for !logs
        return None, str(e)
