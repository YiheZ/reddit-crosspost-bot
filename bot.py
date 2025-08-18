import os
import praw
import json
import sys
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse
from gemini_translate import translate_and_filter_with_gemini

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

FORCE_SUBMIT_SUBS = os.getenv("FORCE_SUBS", "").split(",")
LIMIT_POSTS_DICT = load_json_env("LIMIT_POSTS", {})
DEFAULT_LIMIT_POSTS = 1

TRANSLATE_TARGET_LANG = os.getenv("TRANSLATE_TARGET_LANG", "ZH")
TRANSLATE_SOURCE_LANGS = load_json_env("TRANSLATE_SOURCE_LANGS", {})

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
    now_ts = int(datetime.now(timezone.utc).timestamp())
    clean_data = {}
    for pid, ts in data.get("posted_ids", {}).items():
        if now_ts - ts <= 7*24*3600:  # keep 7 days
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

def get_recent_target_posts(hours=24):
    subreddit = reddit.subreddit(TARGET_SUB)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    posts = [p for p in subreddit.new(limit=200)
             if datetime.fromtimestamp(p.created_utc, timezone.utc) >= cutoff]
    return [p.title for p in posts]

def is_external_link(post):
    url = getattr(post, "url", "")
    internal_domains = ["reddit.com", "i.redd.it", "v.redd.it", "redditmedia.com"]
    return url and not any(d in url for d in internal_domains)

def get_original_post(post):
    """Return the post object to crosspost, and its original title"""
    if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
        orig = post.crosspost_parent_list[0]
        return post, orig.get("title", post.title)
    return post, post.title

def normalize_link(url: str) -> str:
    """Normalize links for duplicate detection (strip trailing slash, lowercase, remove query)."""
    if not url:
        return url
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    normalized = urlunparse((parsed.scheme, netloc, path, '', '', ''))
    return normalized

# -----------------------------
# Main bot logic
# -----------------------------
try:
    seen_links = set()
    all_posts = []

    # Fetch candidates from source subs
    for sub in SOURCE_SUBS:
        posts = get_top_posts_past_day(sub.strip())
        limit = LIMIT_POSTS_DICT.get(sub.strip(), DEFAULT_LIMIT_POSTS)
        filtered = []
        for p in posts:
            if p.id in posted_ids:
                continue
            if p.subreddit.display_name.lower() == TARGET_SUB.lower():
                continue
            if not match_keywords(p.title):
                continue
            norm_url = normalize_link(getattr(p, "url", ""))
            if norm_url in seen_links:
                print(f"⏭ Skipped duplicate link in batch: {p.url}")
                continue
            seen_links.add(norm_url)
            filtered.append(p)
        filtered = filtered[:limit]
        print(f"🔹 r/{sub.strip()}: fetched {len(posts)} posts, {len(filtered)} selected (limit {limit})")
        all_posts.extend(filtered)

    # Get recent titles in target subreddit
    recent_titles = get_recent_target_posts(hours=24)
    print(f"🔹 Recent titles in r/{TARGET_SUB} (past 24h): {len(recent_titles)}")

    # Prepare candidates for Gemini
    candidates = []
    for p in all_posts:
        post_obj, orig_title = get_original_post(p)
        src_lang = TRANSLATE_SOURCE_LANGS.get(p.subreddit.display_name.lower())
        skip_translation = src_lang and src_lang.upper() == TRANSLATE_TARGET_LANG.upper()
        candidates.append({
            "id": p.id,
            "title": orig_title,
            "source_lang": None if skip_translation else src_lang,
            "subreddit": p.subreddit.display_name
        })
        print(f"Candidate prepared: {p.id} | {orig_title} | src_lang={src_lang}")

    # Gemini translate + flair suggestion
    title_map = {}
    if candidates:
        print("🔹 Sending candidates to Gemini for translation and flair suggestion...")
        result = translate_and_filter_with_gemini(candidates, recent_titles, target_lang=TRANSLATE_TARGET_LANG)
        if "error" in result:
            print(f"❌ Gemini error: {result['error']}")
        else:
            title_map = result
            print(f"🔹 Gemini returned {len(title_map)} results")

    # Post loop
    for post in all_posts:
        post_obj, orig_title = get_original_post(post)
        title_to_post = title_map.get(post.id, {}).get("title_translated", orig_title)
        skip = title_map.get(post.id, {}).get("skip", False)
        flair_id = title_map.get(post.id, {}).get("suggested_flair", None)

        print(f"Posting from r/{post.subreddit.display_name}:")
        print(f"  Original title: {orig_title}")
        print(f"  Translated title: {title_to_post}")
        print(f"  Skip: {skip}")
        print(f"  Suggested flair: {flair_id}")

        external = is_external_link(post_obj)

        # Skip if flagged and not external
        if skip and not external:
            print("⏭ Skipped due to similarity with recent posts")
            posted_ids[post.id] = int(datetime.now(timezone.utc).timestamp())
            continue

        # -----------------------------
        # Decide whether to crosspost or submit
        # -----------------------------
        if hasattr(post_obj, "crosspost_parent_list") and post_obj.crosspost_parent_list and not external:
            # Crosspost
            print(f"⏹ Using crosspost logic from r/{post_obj.subreddit.display_name}")
            crosspost_kwargs = {"subreddit": TARGET_SUB, "send_replies": False, "title": title_to_post}
            if flair_id:
                crosspost_kwargs["flair_id"] = flair_id
            post_obj.crosspost(**crosspost_kwargs)
            print(f"✅ Crossposted from r/{post_obj.subreddit.display_name}")
        else:
            # Submit (external or forced sub)
            if post_obj.is_self:
                reddit.subreddit(TARGET_SUB).submit(
                    title=title_to_post,
                    selftext=getattr(post_obj, "selftext", ""),
                    flair_id=flair_id
                )
            else:
                reddit.subreddit(TARGET_SUB).submit(
                    title=title_to_post,
                    url=getattr(post_obj, "url", ""),
                    flair_id=flair_id
                )
            print(f"✅ Submitted (external/force) from r/{post_obj.subreddit.display_name}")

        # Save posted IDs
        posted_ids[post.id] = int(datetime.now(timezone.utc).timestamp())
        if hasattr(post_obj, "crosspost_parent_list") and post_obj.crosspost_parent_list:
            orig_id = post_obj.crosspost_parent_list[0]["id"]
            posted_ids[orig_id] = int(datetime.now(timezone.utc).timestamp())

        time.sleep(random.randint(2,5))

    save_posted_ids(posted_ids)
    print("✅ Done")

except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
