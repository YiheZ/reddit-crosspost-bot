import os
import json
import google.generativeai as genai

# Load API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Model choice (fast + cheaper quota usage)
MODEL_NAME = "gemini-2.5-flash"

# -----------------------------
# Helpers
# -----------------------------
def _build_prompt(texts, target_lang="ZH", source_lang=None):
    """
    Build a translation prompt that keeps tone and style natural.
    We send multiple texts at once in a JSON-friendly format.
    """
    joined = "\n".join([f"{i+1}. {t}" for i, t in enumerate(texts)])
    if source_lang:
        return (
            f"You are a professional translation engine.\n"
            f"Translate the following texts from {source_lang} into {target_lang}.\n"
            f"Keep the same tone, style, and make it sound natural like a native speaker.\n"
            f"Return ONLY a JSON array of translations, nothing else.\n\n"
            f"{joined}"
        )
    else:
        return (
            f"You are a professional translation engine.\n"
            f"Translate the following texts into {target_lang}.\n"
            f"Keep the same tone, style, and make it sound natural like a native speaker.\n"
            f"Return ONLY a JSON array of translations, nothing else.\n\n"
            f"{joined}"
        )

def translate_with_gemini(texts, target_lang="ZH", source_lang=None):
    """
    Translate a list of strings using Gemini.
    Returns: {"texts": [...], "error": ...}
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}

    if not texts:
        return {"texts": []}

    # Ensure list
    if isinstance(texts, str):
        texts = [texts]

    prompt = _build_prompt(texts, target_lang, source_lang)

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)

        output = response.text.strip()

        # Parse JSON safely
        try:
            translations = json.loads(output)
            if isinstance(translations, list) and len(translations) == len(texts):
                return {"texts": translations}
            else:
                return {"error": f"Unexpected response format: {output}"}
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON: {output}"}

    except Exception as e:
        return {"error": str(e)}
