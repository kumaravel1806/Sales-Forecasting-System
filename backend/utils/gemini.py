import os
import requests
from typing import Dict, Any

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-pro')
BASE_URL = 'https://generativelanguage.googleapis.com/v1beta'


def is_configured() -> bool:
    return bool(GEMINI_API_KEY)


def chat_once(prompt: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not is_configured():
        return {"configured": False, "output": "Gemini not configured. Set GEMINI_API_KEY."}

    url = f"{BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    # Add simple context instructions if provided
    if context and isinstance(context, dict) and context.get('system'):
        payload["systemInstruction"] = {"parts": [{"text": str(context['system'])}]}

    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        # Extract first candidate text
        text = None
        try:
            text = data['candidates'][0]['content']['parts'][0].get('text')
        except Exception:
            text = None
        return {"configured": True, "raw": data, "output": text}
    except Exception as e:
        return {"configured": True, "error": str(e), "output": None}

# Alias for backwards compatibility
chat = chat_once
