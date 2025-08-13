import os
import praw
import json
import sys
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from deepl_translate import translate_with_deepl

# Reddit API setup
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=f"auto-crosspost-bot by u/{os.getenv('REDDIT_USERNAME')}",
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

# GitHub Gist setup
GIST_ID = os.getenv("GIST_ID")
MY_GIST_PAT = os.getenv("MY_GIST_PAT")
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {MY_GIST_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

# Configuration variables
SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")
TRANSLATE_SUBS = os.getenv("TRANSLATE_SUBS", "").split(",")
FORCE_SUBMIT_SUBS = os.getenv("FORCE_SUBMIT_SUBS", "").split(",")
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")
EXCLUDE_KEYWORDS = json.loads(os.getenv("EXCLUDE_KEYWORDS", "[]"))
CROSSPOST_FLAIR_ID = os.getenv("CROSSPOST_FLAIR_ID")
TRANSLATE_TARGET_LANG = os.getenv("TRANSLATE_TARGET_LANG", "ZH")
TRANSLATE_SOURCE_LANGS = json.loads(os.getenv("TRANSLATE_SOURCE_LANGS", "{}"))

# LIMIT_POSTS per subreddit, default 3
try:
    LIMIT_POSTS_JSON = os.getenv("LIMIT_POSTS", "{}")
    LIMIT_POSTS_DICT = json.loads(LIMIT_POSTS_JSON)
except json.JSONDecodeError:
    LIMIT_POSTS_DICT = {}
DEFAULT_LIMIT_POSTS = 3

# Load posted IDs from Gist
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

# Helper functions
def match_keywords(title):
    """Return True if the post title does NOT contain any excluded keyword."""
    if not EXCLUDE_KEYWORDS:
        return True  # nothing to exclude
    title_lower = title.lower()
    return not any(kw.lower() in title_lower for kw in EXCLUDE_KEYWORDS if kw)

def get_top_posts_past_day(subreddit_name, max_candidates=500, top_limit=100):
    subreddit = reddit.subreddit(subreddit_name)
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    posts = [p for p in subreddit.new(limit=max_candidates)
             if datetime.fromtimestamp(p.created_utc, timezone.utc) >= one_day_ago]
    posts.sort(key=lambda p: p.score, reverse=True)
    return posts[:top_limit]

# Main crosspost logic
try:
    for sub in SOURCE_SUBS:
        posts = get_top_posts_past_day(sub.strip(), max_candidates=500, top_limit=100)
        crossposted = 0

        # Determine subreddit-specific limit
        sub_limit = LIMIT_POSTS_DICT.get(sub.strip(), DEFAULT_LIMIT_POSTS)

        for post in posts:
            if post.id in posted_ids:
                continue
            if not match_keywords(post.title):
                continue

            title_to_post = post.title

            # Translate title if subreddit requires translation
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

            # Decide between submit() or crosspost()
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

            posted_ids.add(post.id)
            crossposted += 1

            # Random sleep 2–5 seconds between posts
            time.sleep(random.randint(2, 5))

            if crossposted >= sub_limit:
                break

        # Random sleep 5–10 seconds after finishing a subreddit
        time.sleep(random.randint(5, 10))

    save_posted_ids(posted_ids)
    print("✅ Done")
except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
