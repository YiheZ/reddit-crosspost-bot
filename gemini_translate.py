import os
import json
import re
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

DEBUG_PROMPT = os.getenv("DEBUG_PROMPT", "false").lower() == "true"

def _sanitize_json_output(text: str) -> str:
    """Remove code fences and extra whitespace before parsing JSON."""
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.I)
    return text

def _build_prompt(candidates, recent_titles, target_lang="ZH", flair_options=None):
    """
    Build a Gemini prompt to translate Reddit post titles and suggest flairs.
    Body text is included only for context, not for translation.
    """
    lines = []
    for c in candidates:
        src = f"[{c['source_lang']}]" if c.get("source_lang") else ""
        sub = f"(r/{c['subreddit']})"
        line = f"{c['id']}: {src} {c['title']} {sub}"
        if c.get("body"):
            # include body as context only (not for translation)
            line += f"\n  BODY (context only, do not translate): {c['body'][:1000]}"
        lines.append(line)

    recent_joined = "\n".join(recent_titles)
    flair_text = f"Available flairs: {', '.join(flair_options)}\n" if flair_options else ""

    return (
        f"You are a professional translator for Reddit post titles.\n"
        f"Translate the following titles into {target_lang}, keeping them natural and native-sounding.\n"
        f"Do NOT translate the body text, it's provided only as context.\n"
        f"Do NOT add extra punctuation unless natural.\n"
        f"If two or more titles are basically identical in meaning among the candidates, only translate the first one and mark the rest as skip.\n"
        f"Do NOT output titles that duplicate recent posts in the target subreddit.\n"
        f"Recent titles:\n{recent_joined}\n"
        f"{flair_text}"
        f"For each candidate, return a JSON array of objects with:\n"
        f"  - id: post id\n"
        f"  - title_translated: the translated title\n"
        f"  - skip: true/false\n"
        f"  - suggested_flair: pick the most suitable flair from the list\n"
        f"Return ONLY JSON.\n\n"
        f"Candidates:\n" + "\n".join(lines)
    )

def translate_and_filter_with_gemini(candidates, recent_titles, target_lang="ZH", flair_options=None):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}
    if not candidates:
        return {}

    prompt = _build_prompt(candidates, recent_titles, target_lang, flair_options)

    if DEBUG_PROMPT:
        print("🔍 Gemini Prompt:\n", prompt, "\n" + "-"*60)

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
                    "skip": item.get("skip", False),
                    "suggested_flair": item.get("suggested_flair")
                }
            return result
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON: {output}"}
    except Exception as e:
        return {"error": str(e)}
