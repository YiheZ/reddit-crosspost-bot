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

        if c.get("skip_translation"):
            line += f"\n  This post is already in target language. Do NOT translate the title. Keep 'title_translated' and 'content_translated' identical to original."
        if c.get("body"):
            line += f"\n  BODY (context only, do not translate): {c['body'][:10000]}"
        if c.get("url_content"):
            line += f"\n  EXTERNAL CONTENT (from {c['url']}): {c['url_content'][:10000]}"
        elif c.get("url") and ALLOW_GEMINI_FETCH:
            line += f"\n  EXTERNAL CONTENT UNAVAILABLE LOCALLY. If you have browsing capability, summarize directly from URL: {c['url']}"

        lines.append(line)

    recent_joined = "\n".join(recent_titles)
    flair_text = f"Available flairs: {', '.join(flair_options)}\n" if flair_options else ""

    return (
        f"You are a professional translator and news editor for Reddit posts.\n"
        f"Translate and adapt each post title into {target_lang}, ensuring the result is:\n"
        f"  • Natural, fluent, and easy to read\n"
        f"  • Faithful to the original meaning but not word-for-word\n"
        f"  • Styled like a polished news headline in {target_lang}\n"
        f"  • Do NOT add extra commentary, conclusions, imagined quotes, or third-person phrases like '网友热议', '玩家调侃', '玩家呼吁' etc.\n\n"
        f"Context and reference usage:\n"
        f"  • BODY text: Use only as context to clarify or disambiguate the title. Do NOT translate it directly.\n"
        f"  • EXTERNAL CONTENT: Use only as reference to improve accuracy of the translated title.\n"
        f"  • If only a raw URL is given: summarize concisely if browsing is available, otherwise leave 'content_translated' empty.\n\n"
        f"Source subreddit adaptation:\n"
        f"  • Always consider the SOURCE SUBREDDIT (use each candidate’s subreddit) when translating.\n"
        f"  • Resolve ambiguous references (e.g., 'PM', 'the President', 'the government') in a way that fits the subreddit context.\n\n"
        f"Localization rules:\n"
        f"  • Convert measurement units into the local system expected by {target_lang} readers.\n"
        f"  • Round numbers appropriately for news headlines.\n"
        f"  • For country names, use local conventions or standard abbreviations for {target_lang} readers.\n\n"
        f"Summarization rules:\n"
        f"  • Summaries must be concise translations of the content.\n"
        f"  • Do NOT add commentary, interpretations, or stylistic flourishes.\n\n"
        f"Deduplication rules:\n"
        f"  • If multiple titles are essentially the same, translate only the first and set 'skip' = true for the others.\n"
        f"  • Do not output titles that duplicate recent posts.\n\n"
        f"Tone:\n"
        f"  • Adapt the style to match the SOURCE SUBREDDIT, keeping it engaging but professional.\n"
        f"  • A subtle Reddit-style hook is acceptable, but never add outside commentary.\n\n"
        f"Output format:\n"
        f"Return ONLY a valid JSON array of objects with exactly these fields:\n"
        f"  - id\n"
        f"  - title_translated\n"
        f"  - skip (true/false)\n"
        f"  - suggested_flair\n"
        f"  - content_translated\n\n"
        f"Recent titles:\n{recent_joined}\n"
        f"{flair_text}"
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
