import os
import json
import re
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

def _sanitize_json_output(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.I)
    return text

def translate_and_filter_with_gemini(candidates, recent_titles, target_lang="ZH", source_langs=None):
    """
    candidates: list of dicts {"id": post_id, "title": title, "source_lang": "EN"/None}
    recent_titles: list of strings (already posted in target sub)
    Returns: dict of post_id -> {"title_translated": str, "skip": bool}
    """
    prompt_lines = []
    for i, c in enumerate(candidates):
        src_lang = c.get("source_lang")
        if src_lang:
            prompt_lines.append(f"{i+1}. [{src_lang}] {c['title']}")
        else:
            prompt_lines.append(f"{i+1}. {c['title']}")
    joined_candidates = "\n".join(prompt_lines)
    recent_json = json.dumps(recent_titles, ensure_ascii=False)

    prompt = (
        f"You are a professional translator and content filter for a subreddit.\n"
        f"Input candidate post titles:\n{joined_candidates}\n\n"
        f"These titles have been posted in the target subreddit recently:\n{recent_json}\n\n"
        f"Task: For each candidate title, do the following:\n"
        f"1. Translate it into {target_lang} using the target language's usual phrasing for social media/news headlines.\n"
        f"2. Determine if it is semantically very similar to any recent post (ignore minor wording differences).\n"
        f"3. Return ONLY a JSON array with objects like {{\"id\": candidate_id, \"title_translated\": ..., \"skip\": true/false}}, preserving order.\n"
        f"Do not add any extra text, numbers, or punctuation. Do not skip translation unless source language equals target language.\n"
    )

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        output = _sanitize_json_output(response.text)
        result = json.loads(output)
        output_map = {item["id"]: {"title_translated": item["title_translated"], "skip": item["skip"]} for item in result}
        return output_map
    except Exception as e:
        return {"error": str(e)}
