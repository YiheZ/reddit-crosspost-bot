import os
import json
import re
import requests
from bs4 import BeautifulSoup
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

def _fetch_url_content(url: str, max_chars=5000) -> str:
    """Fetch the page content from a URL and return plain text."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Remove scripts/styles
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n")
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars]
    except Exception as e:
        print(f"⚠️ Failed to fetch URL {url}: {e}")
        return ""

def _build_prompt(candidates, recent_titles, target_lang="ZH", flair_options=None):
    """
    Build a Gemini prompt to translate Reddit titles and optionally summarize external content.
    """
    lines = []
    for c in candidates:
        src = f"[{c['source_lang']}]" if c.get("source_lang") else ""
        sub = f"(r/{c['subreddit']})"
        line = f"{c['id']}: {src} {c['title']} {sub}"
        if c.get("body"):
            line += f"\n  BODY (context only, do not translate): {c['body'][:1000]}"
        if c.get("url_content"):
            line += f"\n  EXTERNAL CONTENT (from {c['url']}): {c['url_content'][:1000]}"
        lines.append(line)

    recent_joined = "\n".join(recent_titles)
    flair_text = f"Available flairs: {', '.join(flair_options)}\n" if flair_options else ""

    return (
        f"You are a professional translator and news editor for Reddit posts.\n"
        f"Translate the following titles into {target_lang}, keeping them natural and native-sounding.\n"
        f"When translating, consider the context from the body and/or external URL content so that the translation is accurate, reasonable, "
        f"and aligned with the actual meaning of the post.\n"
        f"Do NOT translate the body text itself; it is provided only as context.\n"
        f"For posts with external URLs, read the linked content and produce a concise, formal, news-agency style summary, like a quick news bulletin. "
        f"Do NOT use phrases like 'this article' or 'the article'; write as a news report, direct and objective.\n"
        f"Include the summary in 'content_translated'. If no content is available, leave it empty.\n"
        f"Do NOT add extra punctuation unless natural.\n"
        f"If two or more titles are essentially identical in meaning among the candidates, translate only the first and mark the rest as skip.\n"
        f"Do NOT output titles that duplicate recent posts in the target subreddit.\n"
        f"Recent titles:\n{recent_joined}\n"
        f"{flair_text}"
        f"IMPORTANT: Consider the SOURCE SUBREDDIT when translating.\n"
        f"For each candidate, return a JSON array of objects with the following fields:\n"
        f"  - id: post id\n"
        f"  - title_translated: the translated title\n"
        f"  - skip: true/false\n"
        f"  - suggested_flair: pick the most suitable flair from the list\n"
        f"  - content_translated: (optional) summarized & translated external content\n"
        f"Return ONLY JSON.\n\n"
        f"Candidates:\n" + "\n".join(lines)
    )

def translate_and_filter_with_gemini(candidates, recent_titles, target_lang="ZH", flair_options=None):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}
    if not candidates:
        return {}

    # Fetch external content if URL is provided
    for c in candidates:
        if c.get("url") and not c.get("url_content"):
            c["url_content"] = _fetch_url_content(c["url"])

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
                    "title_translated": item.get("title_translated"),
                    "skip": item.get("skip", False),
                    "suggested_flair": item.get("suggested_flair"),
                    "content_translated": item.get("content_translated", "")
                }
            return result
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON: {output}"}
    except Exception as e:
        return {"error": str(e)}
