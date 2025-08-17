import os
import json
import google.generativeai as genai
import re

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

def _sanitize_json_output(text: str) -> str:
    """
    Remove code fences and extra whitespace before parsing JSON.
    """
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.I)
    return text

def _build_prompt(texts, target_lang="ZH", source_langs=None):
    """
    Build prompt for Gemini batch translation.
    If source_langs is a list, use corresponding source language per text.
    These texts are subreddit post titles, so translation should be concise, 
    natural, and readable as Reddit titles in the target language.
    """
    joined_lines = []
    for i, t in enumerate(texts):
        src_lang = None
        if isinstance(source_langs, list) and i < len(source_langs):
            src_lang = source_langs[i]
        if src_lang:
            joined_lines.append(f"{i+1}. [{src_lang}] {t}")
        else:
            joined_lines.append(f"{i+1}. {t}")
    joined = "\n".join(joined_lines)

    return (
        f"You are a professional translation engine.\n"
        f"Translate the following subreddit post titles into {target_lang}.\n"
        f"Keep the same tone and style, concise and natural like a native speaker would post on Reddit.\n"
        f"Return ONLY a JSON array of translations, nothing else.\n\n{joined}"
    )

def translate_with_gemini(texts, target_lang="ZH", source_langs=None):
    """
    texts: list of strings
    source_langs: None, str (single language), or list of same length as texts
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}

    if not texts:
        return {"texts": []}

    if isinstance(texts, str):
        texts = [texts]

    # If source_langs is a single string, convert to list
    if isinstance(source_langs, str):
        source_langs = [source_langs] * len(texts)

    prompt = _build_prompt(texts, target_lang, source_langs)

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        output = _sanitize_json_output(response.text)

        try:
            translations = json.loads(output)
            if isinstance(translations, list) and len(translations) == len(texts):
                return {"texts": translations}
            else:
                return {"error": f"Unexpected JSON length: {len(translations)} vs {len(texts)}"}
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON: {output}"}
    except Exception as e:
        return {"error": str(e)}
