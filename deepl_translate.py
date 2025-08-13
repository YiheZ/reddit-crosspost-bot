import os
import requests

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")

def translate_with_deepl(text: str, target_lang: str = "ZH", source_lang: str = None) -> dict:
    """
    Translate text using DeepL API with optional source language.
    Returns dictionary: {"text": translated_text, "detected_language": lang} or {"error": msg}
    """
    if not DEEPL_API_KEY:
        return {"error": "DEEPL_API_KEY not configured"}
    
    url = "https://api-free.deepl.com/v2/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "text": [text],
        "target_lang": target_lang
    }
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
        elif response.status_code == 403:
            return {"error": "Invalid DeepL API Key or usage limit reached"}
        elif response.status_code == 456:
            return {"error": "DeepL free quota limit reached"}
        else:
            return {"error": f"DeepL API Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}
