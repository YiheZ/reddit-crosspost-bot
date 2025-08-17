import os
import json
import re
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

def _sanitize_json_output(text: str) -> str:
    """Remove code fences and extra whitespace before parsing JSON."""
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.I)
    return text

def _build_prompt(candidates, recent_titles, target_lang="ZH"):
    """
    Build a Gemini prompt to translate and filter Reddit post titles.
    candidates: list of dicts {"id": str, "title": str, "source_lang": str or None, "subreddit": str}
    recent_titles: list of titles already posted in target subreddit
    """
    lines = []
    for c in candidates:
        src = f"[{c['source_lang']}]" if c.get("source_lang") else ""
        sub = f"(r/{c['subreddit']})"
        lines.append(f"{c['id']}: {src} {c['title']} {sub}")
    
    recent_joined = "\n".join(recent_titles)

    return (
        f"You are a professional translator for Reddit posts.\n"
        f"Translate the following titles into {target_lang}, keeping the tone and style natural and native-sounding for the subreddit context.\n"
        f"Convert any measurements to local units (e.g., kg, km, °C) if applicable.\n"
        f"Do NOT add a full stop (。) at the end unless it is natural.\n"
        f"Do NOT post titles that are basically identical to any recent titles in the target subreddit.\n"
        f"Check similarity against these recent titles:\n"
        f"{recent_joined}\n\n"
        f"For each candidate, return a JSON array of objects with:\n"
        f"  - id: the post id\n"
        f"  - title_translated: the translated title\n"
        f"  - skip: true if meaning is basically the same as any recent post, false otherwise\n"
        f"Return ONLY JSON.\n\n"
        f"Candidates:\n" + "\n".join(lines)
    )

def translate_and_filter_with_gemini(candidates, recent_titles, target_lang="ZH"):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}
    if not candidates:
        return {}

    prompt = _build_prompt(candidates, recent_titles, target_lang)

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        output = _sanitize_json_output(response.text)

        try:
            parsed = json.loads(output)
            # convert to dict keyed by post id
            result = {}
            for item in parsed:
                pid = item["id"]
                result[pid] = {
                    "title_translated": item["title_translated"],
                    "skip": item.get("skip", False)
                }
            return result
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON: {output}"}
    except Exception as e:
        return {"error": str(e)}
