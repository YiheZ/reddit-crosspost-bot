import os
import requests
import json

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")

def translate_with_deepl(text: str, target_lang: str = "ZH", source_lang: str = None) -> dict:
    """
    Translate text using DeepL API.
    source_lang=None for auto-detect
    Returns dict: {"text": ..., "detected_language": ...} or {"error": ...}
    """
    if not DEEPL_API_KEY:
        return {"error": "DEEPL_API_KEY not configured"}

    url = "https://api-free.deepl.com/v2/translate"
    headers = {"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}", "Content-Type": "application/json"}
    data = {"text": [text], "target_lang": target_lang}
    if source_lang:
        data["source_lang"] = source_lang

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            translation = result["translations"][0]
            return {
                "text": translation["text"],
                "detected_language": translation.get("detected_source_language", "Unknown")
            }
        else:
            return {"error": f"DeepL API error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}
