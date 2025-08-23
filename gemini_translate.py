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

def _build_prompt(candidates, recent_titles, target_lang="ZH", flair_options=None):
    """
    Build a Gemini prompt to translate Reddit post titles (and text bodies if present).
    """
    lines = []
    for c in candidates:
        src = f"[{c['source_lang']}]" if c.get("source_lang") else ""
        sub = f"(r/{c['subreddit']})"
        title_line = f"{c['id']}: {src} {c['title']} {sub}"
        if c.get("body"):
            title_line += f"\n  BODY: {c['body'][:300]}..."  # truncate preview
        lines.append(title_line)

    recent_joined = "\n".join(recent_titles)
    flair_text = f"Available flairs: {', '.join(flair_options)}\n" if flair_options else ""

    return (
        f"You are a professional translator for Reddit posts.\n"
        f"Translate the following Reddit posts into {target_lang}, keeping them natural and native-sounding.\n"
        f"Convert measurements to local units if needed.\n"
        f"Do NOT add punctuation unnaturally.\n"
        f"If multiple posts are duplicates in meaning, only keep the first and mark others as skip.\n"
        f"Do NOT output duplicates of recent subreddit posts.\n"
        f"Recent titles:\n{recent_joined}\n"
        f"{flair_text}"
        f"Return JSON array of objects with:\n"
        f"  - id: post id\n"
        f"  - title_translated\n"
        f"  - body_translated (empty string if no body)\n"
        f"  - skip: true/false\n"
        f"  - suggested_flair\n"
        f"Return ONLY JSON.\n\n"
        f"Candidates:\n" + "\n".join(lines)
    )

def translate_and_filter_with_gemini(candidates, recent_titles, target_lang="ZH", flair_options=None):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}
    if not candidates:
        return {}

    prompt = _build_prompt(candidates, recent_titles, target_lang, flair_options)

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
                    "body_translated": item.get("body_translated", ""),
                    "skip": item.get("skip", False),
                    "suggested_flair": item.get("suggested_flair")
                }
            return result
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON: {output}"}
    except Exception as e:
        return {"error": str(e)}
