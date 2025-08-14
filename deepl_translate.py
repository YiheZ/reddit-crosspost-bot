import os
import requests
import json
import re

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")

def localize_quotes(text: str) -> str:
    """
    Replace remaining English-style quotes with proper Chinese quotes:
    - “ ” for speech
    - 《 》 for works/titles
    """

    # Pattern for speech (after a colon or says-like verbs)
    speech_pattern = re.compile(r'(:|：)\s*[\'"“”](.*?)[\'"“”]$')
    # Pattern for works/titles (inside 《 》 in Chinese)
    work_pattern = re.compile(r'[\'"“”](.*?)[\'"“”]')

    # Try speech detection
    match_speech = speech_pattern.search(text)
    if match_speech:
        quoted = match_speech.group(2)
        # Replace with Chinese speech quotes
        return speech_pattern.sub(lambda m: f"{m.group(1)}“{quoted}”", text)

    # If not speech, check if it's a work title
    match_work = work_pattern.search(text)
    if match_work:
        quoted = match_work.group(1)
        # Replace with Chinese work title quotes
        return work_pattern.sub(f"《{quoted}》", text)

    return text


def translate_with_deepl(text: str, target_lang: str = "ZH", source_lang: str = None) -> dict:
    ...
    if response.status_code == 200:
        result = response.json()
        translation = result["translations"][0]["text"]
        translation = localize_quotes(translation)  # post-process quotes
        return {
            "text": translation,
            "detected_language": result["translations"][0].get("detected_source_language", "Unknown")
        }
