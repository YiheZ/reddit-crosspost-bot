import os
import praw
import json
import sys
import time
import random
import requests
from datetime import datetime, timedelta, timezone
# -----------------------------
# Translation imports
# -----------------------------
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
TRANSLATE_SUBS = os.getenv("TRANSLATE_SUBS", "").split(",")
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
print(f"🔹 Loaded {len(posted_ids)} previously posted IDs.")

# -----------------------------
# Helper functions
# -----------------------------
def match_keywords(title: str) -> bool:
    """
    Return True if the post title matches keyword filters.
    - If INCLUDE_KEYWORDS is non-empty → must contain at least one.
    - Must NOT contain any EXCLUDE_KEYWORDS.
    """
    title_lower = title.lower()

    # Exclude filter
    if any(kw.lower() in title_lower for kw in EXCLUDE_KEYWORDS if kw):
        return False

    # Include filter
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
# Main crosspost logic with logging
# -----------------------------
try:
    # Collect all posts that need translation across all subs first
    all_translation_candidates = []

    # Mapping post.id -> post
    all_posts_map = {}

    for sub in SOURCE_SUBS:
        sub = sub.strip()
        posts = get_top_posts_past_day(sub, max_candidates=500, top_limit=100)
        sub_limit = LIMIT_POSTS_DICT.get(sub, DEFAULT_LIMIT_POSTS)

        print(f"🔹 r/{sub}: fetched {len(posts)} posts from last 24h, top 100 by score.")

        candidates = []
        for post in posts:
            reason_skipped = None
            if post.id in posted_ids:
                reason_skipped = "already posted"
            elif post.subreddit.display_name.lower() == TARGET_SUB.lower():
                reason_skipped = f"from target subreddit {TARGET_SUB}"
            elif not match_keywords(post.title):
                reason_skipped = "excluded by keywords"

            if reason_skipped:
                print(f"⚠️ Skipped ({reason_skipped}): {post.title}")
                continue

            candidates.append(post)
            all_posts_map[post.id] = post

            if len(candidates) >= sub_limit:
                break

        print(f"🔹 r/{sub}: {len(candidates)} posts selected for posting (limit {sub_limit}).")
        all_translation_candidates.extend(candidates)

    # -----------------------------
    # Batch translation with Gemini
    # -----------------------------
    title_map = {}
    if all_translation_candidates:
        posts_needing_translation = [
            p for p in all_translation_candidates if p.subreddit.display_name.lower() in [s.lower() for s in TRANSLATE_SUBS]
        ]
        if posts_needing_translation:
            titles_to_translate = [p.title for p in posts_needing_translation]
            # Determine source languages for each post
            source_langs = [TRANSLATE_SOURCE_LANGS.get(p.subreddit.display_name.lower()) for p in posts_needing_translation]
            result = translate_with_gemini(
                titles_to_translate,
                target_lang=TRANSLATE_TARGET_LANG,
                source_langs=source_langs
            )
            if "texts" in result:
                title_map = {p.id: result["texts"][i] for i, p in enumerate(posts_needing_translation)}
            else:
                print(f"⚠️ Translation error: {result.get('error')} (posting original titles)")

    # -----------------------------
    # Post to Reddit
    # -----------------------------
    for post in all_posts_map.values():
        title_to_post = title_map.get(post.id, post.title)
        sub = post.subreddit.display_name

        if sub.lower() in [s.lower() for s in FORCE_SUBMIT_SUBS]:
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
            if sub.lower() in [s.lower() for s in TRANSLATE_SUBS]:
                crosspost_kwargs["title"] = title_to_post
            post.crosspost(**crosspost_kwargs)
            print(f"✅ Crossposted from r/{sub}: {title_to_post}")

        posted_ids.add(post.id)
        # Random sleep 2–5 seconds between posts
        time.sleep(random.randint(2, 5))

    # -----------------------------
    # Save posted IDs
    # -----------------------------
    save_posted_ids(posted_ids)
    print("✅ Done")

except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
