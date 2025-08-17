import os
import praw
import json
import sys
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from deepl_translate import translate_with_deepl

# -----------------------------
# Helper to safely load JSON env variables
# -----------------------------
def load_json_env(var_name, default="[]"):
    val = os.getenv(var_name, "").strip()
    if not val:
        val = default
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        print(f"⚠️ Warning: Invalid JSON for {var_name}, using default {default}")
        return json.loads(default)

# -----------------------------
# Reddit API setup
# -----------------------------
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=f"auto-crosspost-bot by u/{os.getenv('REDDIT_USERNAME')}",
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

# -----------------------------
# GitHub Gist setup for posted IDs
# -----------------------------
GIST_ID = os.getenv("GIST_ID")
MY_GIST_PAT = os.getenv("MY_GIST_PAT")
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {MY_GIST_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

# -----------------------------
# Configuration variables
# -----------------------------
SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")
TRANSLATE_SUBS = os.getenv("TRANSLATE_SUBS", "").split(",")
FORCE_SUBMIT_SUBS = os.getenv("FORCE_SUBMIT_SUBS", "").split(",")
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")

EXCLUDE_KEYWORDS = load_json_env("EXCLUDE_KEYWORDS", "[]")
INCLUDE_KEYWORDS = load_json_env("INCLUDE_KEYWORDS", "[]")
CROSSPOST_FLAIR_ID = os.getenv("CROSSPOST_FLAIR_ID")
TRANSLATE_TARGET_LANG = os.getenv("TRANSLATE_TARGET_LANG", "ZH")
TRANSLATE_SOURCE_LANGS = load_json_env("TRANSLATE_SOURCE_LANGS", "{}")
LIMIT_POSTS_DICT = load_json_env("LIMIT_POSTS", "{}")
DEFAULT_LIMIT_POSTS = 3

# -----------------------------
# Load posted IDs from Gist
# -----------------------------
def load_posted_ids():
    response = requests.get(GIST_API_URL, headers=HEADERS)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to load posted IDs: {response.status_code} {response.text}")
    gist_data = response.json()
    files = gist_data.get("files", {})
    content = files.get("posted_ids.json", {}).get("content", "{}")
    data = json.loads(content)
    # Remove posts older than 7 days automatically
    now_ts = int(datetime.now(timezone.utc).timestamp())
    posted = {pid: ts for pid, ts in data.get("posted_ids", {}).items() if now_ts - ts <= 7 * 24 * 3600}
    return posted

def save_posted_ids(posted_ids):
    payload = {"files": {"posted_ids.json": {"content": json.dumps({"posted_ids": posted_ids}, indent=2)}}}
    response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to save posted IDs: {response.status_code} {response.text}")

posted_ids = load_posted_ids()

# -----------------------------
# Helper functions
# -----------------------------
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
# Main crosspost logic
# -----------------------------
try:
    for sub in SOURCE_SUBS:
        posts = get_top_posts_past_day(sub.strip(), max_candidates=500, top_limit=100)
        crossposted = 0
        sub_limit = LIMIT_POSTS_DICT.get(sub.strip(), DEFAULT_LIMIT_POSTS)

        for post in posts:
            if post.id in posted_ids:
                continue
            if post.subreddit.display_name.lower() == TARGET_SUB.lower():
                continue
            if not match_keywords(post.title):
                continue

            title_to_post = post.title

            # Translate title if needed
            if sub.strip() in TRANSLATE_SUBS:
                source_lang = TRANSLATE_SOURCE_LANGS.get(sub.strip())
                result = translate_with_deepl(
                    post.title,
                    target_lang=TRANSLATE_TARGET_LANG,
                    source_lang=source_lang
                )
                if "error" not in result:
                    title_to_post = result["text"]
                    print(f"Translated '{post.title}' -> '{title_to_post}' (detected: {result.get('detected_language')})")
                else:
                    print(f"Translation error: {result['error']} (posting original title)")

            # Submit or crosspost
            if sub.strip() in FORCE_SUBMIT_SUBS:
                reddit.subreddit(TARGET_SUB).submit(
                    title=title_to_post,
                    url=post.url,
                    flair_id=CROSSPOST_FLAIR_ID if CROSSPOST_FLAIR_ID else None
                )
                print(f"✅ Submitted (force submit) from r/{sub}: {title_to_post}")
            else:
                crosspost_kwargs = {"subreddit": TARGET_SUB, "send_replies": False}
                if CROSSPOST_FLAIR_ID:
                    crosspost_kwargs["flair_id"] = CROSSPOST_FLAIR_ID
                if sub.strip() in TRANSLATE_SUBS:
                    crosspost_kwargs["title"] = title_to_post
                post.crosspost(**crosspost_kwargs)
                print(f"✅ Crossposted from r/{sub}: {title_to_post}")

            posted_ids[post.id] = int(datetime.now(timezone.utc).timestamp())
            crossposted += 1

            time.sleep(random.randint(2, 5))
            if crossposted >= sub_limit:
                break

        time.sleep(random.randint(5, 10))

    save_posted_ids(posted_ids)
    print("✅ Done")

except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
