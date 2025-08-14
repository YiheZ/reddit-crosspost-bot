import os
import requests
import json

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")

# Distinct opening→closing pairs (Chinese & common brackets)
PAIRS = {
    "《": "》",
    "“": "”",
    "‘": "’",
    "「": "」",
    "『": "』",
    "〈": "〉",
    "（": "）",  # full-width parentheses
    "(": ")",
    "[": "]",
    "{": "}",
}
REVERSE = {v: k for k, v in PAIRS.items()}

SYMMETRIC_QUOTES = {"'", '"'}

def _fix_missing_pairs(text: str) -> str:
    """
    Fix unmatched Chinese/ASCII bracket pairs inside the text:
    - Prepend missing openers for stray closers.
    - Append missing closers for unmatched openers.
    """
    stack = []
    prefix_needed = []

    for ch in text:
        if ch in PAIRS:  # opener
            stack.append(ch)
        elif ch in REVERSE:  # closer
            if stack and PAIRS.get(stack[-1]) == ch:
                stack.pop()
            else:
                # unmatched closer → prepend missing opener
                prefix_needed.append(REVERSE[ch])

    # for any remaining openers in stack → append closers (reverse order)
    suffix_needed = [PAIRS[o] for o in reversed(stack)]

    if prefix_needed:
        text = "".join(prefix_needed) + text
    if suffix_needed:
        text = text + "".join(suffix_needed)

    return text

def _fix_edge_symmetric_quotes(text: str) -> str:
    """
    Carefully fix odd counts of straight quotes only when they
    appear at the very start or very end of the string.
    (Avoids adding quotes for apostrophes in the middle of words.)
    """
    if not text:
        return text

    for q in SYMMETRIC_QUOTES:
        cnt = text.count(q)
        if cnt % 2 == 1:  # unbalanced
            if text.startswith(q):
                text = text + q
            elif text.endswith(q):
                text = q + text
            # else: ignore (likely an apostrophe inside a word)

    return text

def _fix_missing_brackets(translated: str) -> str:
    """Run all post-fixes on translated text."""
    translated = translated.strip()
    if not translated:
        return translated
    translated = _fix_missing_pairs(translated)
    translated = _fix_edge_symmetric_quotes(translated)
    return translated

def translate_with_deepl(text: str, target_lang: str = "ZH", source_lang: str = None) -> dict:
    """
    Translate text using DeepL API (JSON) with full localization.
    After translation, auto-fix any missing matching bracket/quote.
    Returns: {"text": ..., "detected_language": ...} or {"error": ...}
    """
    if not DEEPL_API_KEY:
        return {"error": "DEEPL_API_KEY not configured"}

    if not text:
        return {"text": "", "detected_language": "Unknown"}

    url = "https://api-free.deepl.com/v2/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"text": [text], "target_lang": target_lang}
    if source_lang:
        payload["source_lang"] = source_lang

    try:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            result = resp.json()
            translation = result["translations"][0]["text"]
            detected = result["translations"][0].get("detected_source_language", "Unknown")

            # Post-process to fill any missing matching brackets/quotes
            translation = _fix_missing_brackets(translation)

            return {"text": translation, "detected_language": detected}
        else:
            return {"error": f"DeepL API error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}
