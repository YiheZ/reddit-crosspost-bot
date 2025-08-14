import requests
import re

DEEPL_API_KEY = "YOUR_DEEPL_API_KEY"  # put your key here

def localize_quotes(text: str) -> str:
    """
    Replace remaining English-style quotes with proper Chinese quotes:
    - “ ” for speech
    - 《 》 for works/titles
    """
    # Speech pattern: colon or says-like verb before quotes
    speech_pattern = re.compile(r'(:|：)\s*[\'"“”](.*?)[\'"“”]')
    # Work/title pattern
    work_pattern = re.compile(r'[\'"“”](.*?)[\'"“”]')

    # Detect and replace speech quotes
    if speech_pattern.search(text):
        text = speech_pattern.sub(lambda m: f"{m.group(1)}“{m.group(2)}”", text)

    # Replace any remaining quotes with 《 》
    text = work_pattern.sub(lambda m: f"《{m.group(1)}》", text)

    return text


def translate_with_deepl(text: str, target_lang: str = "ZH", source_lang: str = None) -> dict:
    url = "https://api-free.deepl.com/v2/translate"
    payload = {
        "auth_key": DEEPL_API_KEY,
        "text": text,
        "target_lang": target_lang
    }
    if source_lang:
        payload["source_lang"] = source_lang

    # Call DeepL API
    response = requests.post(url, data=payload)

    if response.status_code == 200:
        result = response.json()
        translation = result["translations"][0]["text"]
        translation = localize_quotes(translation)  # fix quotes
        return {
            "text": translation,
            "detected_language": result["translations"][0].get("detected_source_language", "Unknown")
        }
    else:
        raise RuntimeError(f"DeepL API error {response.status_code}: {response.text}")
