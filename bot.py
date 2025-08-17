import os
import praw
import json
import sys
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from gemini_translate import translate_with_gemini

# -----------------------------
# Helper: safely load JSON env
# -----------------------------
def load_json_env(env_name, default):
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON in {env_name}, using default {default}")
        return default

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
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")

INCLUDE_KEYWORDS = load_json_env("INCLUDE_KEYWORDS", [])
EXCLUDE_KEYWORDS = load_json_env("EXCLUDE_KEYWORDS", [])

CROSSPOST_FLAIR_ID = os.getenv("CROSSPOST_FLAIR_ID", "")
TRANSLATE_TARGET_LANG = os.getenv("TRANSLATE_TARGET_LANG", "ZH")
TRANSLATE_SOURCE_LANGS = load_json_env("TRANSLATE_SOURCE_LANGS", {})

FORCE_SUBMIT_SUBS = os.getenv("FORCE_SUBMIT_SUBS", "").split(",")

try:
    LIMIT_POSTS_DICT = load_json_env("LIMIT_POSTS", {})
except Exception:
    LIMIT_POSTS_DICT = {}
DEFAULT_LIMIT_POSTS = 3

# -----------------------------
# Load posted IDs from Gist
# -----------------------------
def load_posted_ids():
    response = requests.get(GIST_API_URL, headers=HEADERS)
    if response.status_code != 200:
        print(f"⚠️ Failed to load posted IDs: {response.status_code} {response.text}")
        return {}
    gist_data = response.json()
    files = gist_data.get("files", {})
    content = files.get("posted_ids.json", {}).get("content", "{}")
    data = json.loads(content)
    # Clean old posts (>7 days)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    clean_data = {}
    for pid, ts in data.get("posted_ids", {}).items():
        if now_ts - ts <= 7 * 24 * 3600:
            clean_data[pid] = ts
    return clean_data

def save_posted_ids(posted_ids):
    payload = {"files": {"posted_ids.json": {"content": json.dumps({"posted_ids": posted_ids}, indent=2)}}}
    response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to save posted IDs: {response.status_code} {response.text}")

posted_ids = load_posted_ids()
print(f"🔹 Loaded {len(posted_ids)} previously posted IDs.")

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
    # Fetch and filter all posts first
    all_posts = []
    for sub in SOURCE_SUBS:
        posts = get_top_posts_past_day(sub.strip(), max_candidates=500, top_limit=100)
        limit = LIMIT_POSTS_DICT.get(sub.strip(), DEFAULT_LIMIT_POSTS)
        filtered = [p for p in posts if p.id not in posted_ids
                    and p.subreddit.display_name.lower() != TARGET_SUB.lower()
                    and match_keywords(p.title)]
        filtered = filtered[:limit]
        print(f"🔹 r/{sub.strip()}: fetched {len(posts)} posts, {len(filtered)} selected for posting (limit {limit}).")
        all_posts.extend(filtered)

    # Prepare source languages per post (auto-detect by default)
    posts_to_translate = []
    source_langs_list = []
    for p in all_posts:
        src_lang = TRANSLATE_SOURCE_LANGS.get(p.subreddit.display_name.lower())
        if src_lang and src_lang.upper() == TRANSLATE_TARGET_LANG.upper():
            continue  # Skip translation if source = target
        posts_to_translate.append(p)
        source_langs_list.append(src_lang)  # can be None for auto-detect

    # Batch translation
    title_map = {}
    if posts_to_translate:
        texts = [p.title for p in posts_to_translate]
        result = translate_with_gemini(texts, target_lang=TRANSLATE_TARGET_LANG, source_langs=source_langs_list)
        if "texts" in result:
            title_map = {p.id: result["texts"][i] for i, p in enumerate(posts_to_translate)}
        else:
            print(f"Translation error: {result.get('error')} (posting original titles)")

    # Post each
    for post in all_posts:
        original_title = post.title
        title_to_post = title_map.get(post.id, original_title)

        print(f"Posting from r/{post.subreddit.display_name}:")
        print(f"  Original title: {original_title}")
        print(f"  Title to post: {title_to_post}")

        if post.subreddit.display_name.lower() in [s.lower() for s in FORCE_SUBMIT_SUBS]:
            reddit.subreddit(TARGET_SUB).submit(
                title=title_to_post,
                url=post.url,
                flair_id=CROSSPOST_FLAIR_ID if CROSSPOST_FLAIR_ID else None
            )
            print(f"✅ Submitted (force submit) from r/{post.subreddit.display_name}: {title_to_post}")
        else:
            crosspost_kwargs = {"subreddit": TARGET_SUB, "send_replies": False}
            if CROSSPOST_FLAIR_ID:
                crosspost_kwargs["flair_id"] = CROSSPOST_FLAIR_ID
            crosspost_kwargs["title"] = title_to_post
            post.crosspost(**crosspost_kwargs)
            print(f"✅ Crossposted from r/{post.subreddit.display_name}: {title_to_post}")

        posted_ids[post.id] = int(datetime.now(timezone.utc).timestamp())
        time.sleep(random.randint(2, 5))

    save_posted_ids(posted_ids)
    print("✅ Done")
except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
