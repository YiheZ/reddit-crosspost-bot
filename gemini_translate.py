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
ALLOW_GEMINI_FETCH = os.getenv("ALLOW_GEMINI_FETCH", "true").lower() == "true"

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
    """Build Gemini prompt for translation and content summarization."""
    lines = []
    for c in candidates:
        src = f"[{c.get('source_lang','')}]"
        sub = f"(r/{c['subreddit']})"
        line = f"{c['id']}: {src} {c['title']} {sub}"

        if c.get("body"):
            line += f"\n  BODY (context only, do not translate): {c['body'][:5000]}"

        if c.get("url_content"):
            line += f"\n  EXTERNAL CONTENT (from {c['url']}): {c['url_content'][:5000]}"
        elif c.get("url") and ALLOW_GEMINI_FETCH:
            line += f"\n  EXTERNAL CONTENT UNAVAILABLE LOCALLY. If you have browsing capability, summarize directly from URL: {c['url']}"

        lines.append(line)

    recent_joined = "\n".join(recent_titles)
    flair_text = f"Available flairs: {', '.join(flair_options)}\n" if flair_options else ""

    return (
        f"You are a professional translator and news editor for Reddit posts.\n"
        f"Translate the following titles into {target_lang}, keeping them natural and native-sounding.\n"
        f"When translating, consider context from the body and/or external URL content so translation is accurate.\n"
        f"Do NOT translate the body text itself; it is context only.\n"
        f"For posts with external URLs, use the provided EXTERNAL CONTENT. "
        f"If only a raw URL is provided, attempt to summarize it if browsing is available; else leave content_translated empty.\n"
        f"Write the summary in concise, formal, news-agency style. Avoid 'this article' phrasing.\n"
        f"Include summary in 'content_translated'.\n"
        f"Do NOT add extra punctuation unless natural.\n"
        f"If multiple titles are essentially identical, translate only the first and mark the rest as skip.\n"
        f"Do NOT output titles duplicating recent posts.\n"
        f"Recent titles:\n{recent_joined}\n"
        f"{flair_text}"
        f"Consider the SOURCE SUBREDDIT when translating.\n"
        f"Return a JSON array of objects with:\n"
        f"  - id\n"
        f"  - title_translated\n"
        f"  - skip\n"
        f"  - suggested_flair\n"
        f"  - content_translated\n"
        f"Return ONLY JSON.\n\n"
        f"Candidates:\n" + "\n".join(lines)
    )

def translate_and_filter_with_gemini(candidates, recent_titles, target_lang="ZH", flair_options=None):
    """Main pipeline: fetch URLs locally, fallback to Gemini if needed, translate titles."""
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}
    if not candidates:
        return {}

    # Try to fetch external content locally
    for c in candidates:
        if c.get("url") and not c.get("url_content"):
            content = _fetch_url_content(c["url"])
            if content:
                c["url_content"] = content
            # else: fallback handled in _build_prompt if ALLOW_GEMINI_FETCH=True

    prompt = _build_prompt(candidates, recent_titles, target_lang, flair_options)

    if DEBUG_PROMPT:
        print("🔍 Gemini Prompt:\n", prompt, "\n" + "-"*60)

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        output = _sanitize_json_output(response.text)

        try:
            parsed = json.loads(output)
            # Convert to dict keyed by post id
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
