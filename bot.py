import os
import praw
import json
import sys
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from gemini_translate import translate_with_gemini

def load_json_env(env_name, default):
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON in {env_name}, using default {default}")
        return default

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=f"auto-crosspost-bot by u/{os.getenv('REDDIT_USERNAME')}",
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

GIST_ID = os.getenv("GIST_ID")
MY_GIST_PAT = os.getenv("MY_GIST_PAT")
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {MY_GIST_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")

INCLUDE_KEYWORDS = load_json_env("INCLUDE_KEYWORDS", [])
EXCLUDE_KEYWORDS = load_json_env("EXCLUDE_KEYWORDS", [])

CROSSPOST_FLAIR_ID = os.getenv("CROSSPOST_FLAIR_ID", "")
TRANSLATE_SUBS = os.getenv("TRANSLATE_SUBS", "").split(",")
TRANSLATE_TARGET_LANG = os.getenv("TRANSLATE_TARGET_LANG", "ZH")
TRANSLATE_SOURCE_LANGS = load_json_env("TRANSLATE_SOURCE_LANGS", {})

FORCE_SUBMIT_SUBS = os.getenv("FORCE_SUBMIT_SUBS", "").split(",")

try:
    LIMIT_POSTS_DICT = load_json_env("LIMIT_POSTS", {})
except Exception:
    LIMIT_POSTS_DICT = {}
DEFAULT_LIMIT_POSTS = 3

def load_posted_ids():
    response = requests.get(GIST_API_URL, headers=HEADERS)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to load posted IDs: {response.status_code} {response.text}")
    gist_data = response.json()
    files = gist_data.get("files", {})
    content = files.get("posted_ids.json", {}).get("content", "{}")
    data = json.loads(content)
    return set(data.get("posted_ids", []))

def save_posted_ids(posted_ids):
    payload = {"files": {"posted_ids.json": {"content": json.dumps({"posted_ids": list(posted_ids)}, indent=2)}}}
    response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to save posted IDs: {response.status_code} {response.text}")

posted_ids = load_posted_ids()

def match_keywords(title: str) -> bool:
    title_lower = title.lower()
    if any(kw.lower() in title_lower for kw in EXCLUDE_KEYWORDS if kw):
        return False
    if INCLUDE_KEYWORDS:
        return any(kw.lower() in title_lower for kw in INCLUDE_KEYWORDS if kw)
    return True

def get_top_posts_past_day(subreddit_name, max_candidates=500, top_limit=100):
    subreddit = reddit.subreddit(subreddit_name)
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    posts = [p for p in subreddit.new(limit=max_candidates)
             if datetime.fromtimestamp(p.created_utc, timezone.utc) >= one_day_ago]
    posts.sort(key=lambda p: p.score, reverse=True)
    return posts[:top_limit]

# -----------------------------
# Main logic
# -----------------------------
try:
    all_posts_to_post = []
    sub_limits = {}
    
    # Step 1: Collect posts per sub, filter & respect limits
    for sub in SOURCE_SUBS:
        posts = get_top_posts_past_day(sub.strip(), max_candidates=500, top_limit=100)
        sub_limit = LIMIT_POSTS_DICT.get(sub.strip(), DEFAULT_LIMIT_POSTS)
        sub_limits[sub.strip()] = sub_limit

        filtered = [
            p for p in posts
            if p.id not in posted_ids
            and p.subreddit.display_name.lower() != TARGET_SUB.lower()
            and match_keywords(p.title)
        ][:sub_limit]  # Respect per-sub limit here

        all_posts_to_post.extend(filtered)

    # Step 2: Batch translate only posts needing translation
    posts_for_translation = [p for p in all_posts_to_post if p.subreddit.display_name in TRANSLATE_SUBS]
    title_map = {}
    if posts_for_translation:
        titles_to_translate = [p.title for p in posts_for_translation]
        # Determine source_lang per subreddit
        source_langs = [TRANSLATE_SOURCE_LANGS.get(p.subreddit.display_name) for p in posts_for_translation]
        # If all source_lang are same, pass it; otherwise None
        unique_langs = set(filter(None, source_langs))
        source_lang = unique_langs.pop() if len(unique_langs) == 1 else None

        result = translate_with_gemini(
            titles_to_translate,
            target_lang=TRANSLATE_TARGET_LANG,
            source_lang=source_lang
        )
        if "texts" in result:
            title_map = {p.id: result["texts"][i] for i, p in enumerate(posts_for_translation)}
        else:
            print(f"Translation error: {result.get('error')} (posting original titles)")

    # Step 3: Post each sub respecting limits
    for sub in SOURCE_SUBS:
        sub_posts = [p for p in all_posts_to_post if p.subreddit.display_name.lower() == sub.strip().lower()]
        crossposted = 0
        sub_limit = sub_limits.get(sub.strip(), DEFAULT_LIMIT_POSTS)

        for post in sub_posts:
            title_to_post = title_map.get(post.id, post.title)

            if sub.strip() in FORCE_SUBMIT_SUBS:
                reddit.subreddit(TARGET_SUB).submit(
                    title=title_to_post,
                    url=post.url,
                    flair_id=CROSSPOST_FLAIR_ID if CROSSPOST_FLAIR_ID else None
                )
                print(f"✅ Submitted (force submit) from r/{sub}: {title_to_post}")
            else:
                crosspost_kwargs = {"subreddit": TARGET_SUB, "send_re
