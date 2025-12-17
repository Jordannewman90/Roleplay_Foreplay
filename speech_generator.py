import os
import wave
import io
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SPEECH_MODEL_ID = 'gemini-2.5-flash-preview-tts'

def generate_speech(text, voice_name='Kore'):
    """
    Generates speech audio from text using Gemini TTS.
    Returns: (wav_bytes, error_message)
    """
    try:
        response = client.models.generate_content(
            model=SPEECH_MODEL_ID,
            contents=text,
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
        
        # specific to 2.5 flash tts structure
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if part.inline_data:
                pcm_data = part.inline_data.data
                
                # Convert PCM to WAV
                # Gemini TTS output format: 24kHz, 1 channel, 16-bit PCM (usually)
                # The user's snippet suggests: channels=1, rate=24000, sample_width=2
                
                with io.BytesIO() as wav_io:
                    with wave.open(wav_io, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2) # 16-bit
                        wf.setframerate(24000)
                        wf.writeframes(pcm_data)
                    
                    return wav_io.getvalue(), None
                    
        return None, "No audio data returned from API."

    except Exception as e:
        return None, str(e)
