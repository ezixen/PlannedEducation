import os
from google import genai
from google.genai import types
from openai import OpenAI
from . import models

# Fallback API keys for free tier (Global default if teacher hasn't set one)
DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "dummy_gemini_key")

def get_ai_response(user: models.User, prompt: str, image_bytes: bytes = None, audio_bytes: bytes = None) -> str:
    """
    Unified AI wrapper that respects the teacher's AI provider settings.
    We instruct the AI heavily on its role.
    """
    
    system_prompt = (
        "You are an expert, objective teacher and AI grader working for the PlannedEducation platform. "
        "Your job is to assist teachers in grading exams, grouping mistakes, and transcribing handwritten math "
        "or audio feedback. You must be strictly objective, unbiased, and format your output cleanly. "
        "You are processing anonymized data to protect student privacy."
    )
    
    provider = user.ai_provider or "gemini"
    api_key = user.ai_api_key
    model_name = user.ai_model_name
    base_url = user.ai_base_url
    
    if provider == "gemini":
        key = api_key if api_key else DEFAULT_GEMINI_KEY
        client = genai.Client(api_key=key)
        
        contents = [system_prompt, prompt]
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
        if audio_bytes:
            contents.append(types.Part.from_bytes(data=audio_bytes, mime_type="audio/mpeg"))
            
        response = client.models.generate_content(
            model=model_name or "gemini-2.5-flash",
            contents=contents
        )
        return response.text
        
    elif provider in ["openrouter", "ollama", "openai"]:
        # Use OpenAI SDK which supports all 3
        # OpenRouter base URL: https://openrouter.ai/api/v1
        # Ollama base URL: http://localhost:11434/v1
        client = OpenAI(
            base_url=base_url if base_url else (
                "https://openrouter.ai/api/v1" if provider == "openrouter" else 
                "http://localhost:11434/v1" if provider == "ollama" else None
            ),
            api_key=api_key if api_key else "dummy" # Ollama doesn't strictly need one
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        if image_bytes or audio_bytes:
            return "Error: Image/Audio processing is currently only supported via Gemini provider."
            
        response = client.chat.completions.create(
            model=model_name if model_name else "gpt-3.5-turbo",
            messages=messages
        )
        return response.choices[0].message.content
        
    else:
        return "Error: Unknown AI Provider configured."
