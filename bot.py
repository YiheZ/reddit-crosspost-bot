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

TRANSLATE_TARGET_LANG = os.getenv("TRANSLATE_TARGET_LANG", "ZH")
TRANSLATE_SOURCE_LANGS = load_json_env("TRANSLATE_SOURCE_LANGS", {})

FETCH_MODE = os.getenv("FETCH_MODE", "popular").lower()

LIMIT_POSTS_DICT = load_json_env("LIMIT_POSTS", {})
DEFAULT_LIMIT_POSTS = 1

MAX_RETRIES = 3

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
        if now_ts - ts <= 7*24*3600:
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

def fetch_posts(subreddit_name, max_candidates=500, top_limit=100):
    subreddit = reddit.subreddit(subreddit_name)
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)

    if FETCH_MODE == "latest":
        posts = [p for p in subreddit.new(limit=max_candidates)
                 if datetime.fromtimestamp(p.created_utc, timezone.utc) >= one_day_ago]
        posts.sort(key=lambda p: p.created_utc, reverse=True)
        return posts[:top_limit]

    else:
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
    if hasattr(post, 'crosspost_parent_list') and post.crosspost_parent_list:
        original_post = post.crosspost_parent_list[0]
        if original_post.get('is_self', False):
            return False
        url_to_check = original_post.get('url', '')
    else:
        if post.is_self:
            return False
        url_to_check = post.url

    if url_to_check.startswith('/r/'):
        return False

    internal_domains = ["reddit.com", "i.redd.it", "v.redd.it", "redditmedia.com"]
    return not any(d in url_to_check for d in internal_domains)

def get_original_post_title(post):
    if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
        return post.crosspost_parent_list[0]["title"]
    return post.title

def normalize_link(url: str) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    normalized = urlunparse((parsed.scheme, netloc, path, '', '', ''))
    return normalized

def fetch_target_flairs():
    subreddit = reddit.subreddit(TARGET_SUB)
    flairs = []
    for f in subreddit.flair.link_templates:
        if f["text"]:
            flairs.append({"text": f["text"], "id": f["id"]})
    return flairs

flairs = fetch_target_flairs()
flair_options = [f["text"] for f in flairs]
print(f"🔹 Available flairs in r/{TARGET_SUB}: {flair_options}")

# -----------------------------
# Retry posting function
# -----------------------------
def process_posts(posts, title_map, flairs, posted_ids, recent_titles, retries=0):
    failed = []
    now_ts = int(datetime.now(timezone.utc).timestamp())

    for post in posts:
        try:
            if post.id in posted_ids:
                continue

            entry = title_map.get(post.id, {})
            title_to_post = entry.get("title_translated", post.title)
            skip = entry.get("skip", False)
            suggested_flair = entry.get("suggested_flair")

            flair_id = None
            for f in flairs:
                if suggested_flair and suggested_flair in f["text"]:
                    flair_id = f["id"]
                    break

            # ✅ Intentionally skipped posts (always add to Gist immediately)
            if skip:
                print(f"⏭ Intentionally skipped {post.id}")
                posted_ids[post.id] = now_ts
                continue

            # ⚠️ Missing info -> treat as error -> retry
            if not title_to_post or not flair_id:
                print(f"⚠️ Missing translation/flair for {post.id} – will retry")
                failed.append(post)
                continue

            # Try posting
            if is_external_link(post):
                reddit.subreddit(TARGET_SUB).submit(
                    title=title_to_post, url=post.url, flair_id=flair_id
                )
                print(f"✅ Submitted external link: {title_to_post}")
            
            elif post.is_self:  # text/self post
                body_to_post = entry.get("body_translated", post.selftext or "")
                reddit.subreddit(TARGET_SUB).submit(
                    title=title_to_post, selftext=body_to_post, flair_id=flair_id
                )
                print(f"✅ Submitted text post: {title_to_post}")
            
            else:  # media / crosspost
                post_to_cross = post
                if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
                    orig_id = post.crosspost_parent_list[0]["id"]
                    post_to_cross = reddit.submission(id=orig_id)
                post_to_cross.crosspost(
                    subreddit=TARGET_SUB, send_replies=False,
                    title=title_to_post, flair_id=flair_id
                )
                print(f"✅ Crossposted: {title_to_post}")

            posted_ids[post.id] = now_ts
            if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
                posted_ids[post.crosspost_parent_list[0]["id"]] = now_ts

            time.sleep(random.randint(2, 5))

        except Exception as e:
            print(f"⚠️ Failed on post {post.id}: {e}")
            failed.append(post)

    # Retry logic for errors only
    if failed and retries < MAX_RETRIES:
        print(f"🔁 Retrying {len(failed)} failed posts (attempt {retries+1}/{MAX_RETRIES})...")
        candidates = [
            {"id": p.id, "title": get_original_post_title(p),
             "source_lang": None, "subreddit": p.subreddit.display_name}
            for p in failed if p.id not in posted_ids
        ]
        new_map = translate_and_filter_with_gemini(
            candidates, recent_titles,
            target_lang=TRANSLATE_TARGET_LANG, flair_options=[f["text"] for f in flairs]
        )
        process_posts(failed, new_map, flairs, posted_ids, recent_titles, retries=retries+1)

    elif failed:
        # Final retry exhausted -> add to Gist
        print(f"❌ Max retries reached, marking {len(failed)} posts as failed")
        for p in failed:
            posted_ids[p.id] = now_ts

# -----------------------------
# Main bot logic
# -----------------------------
try:
    seen_links = set()
    all_posts = []

    for sub in SOURCE_SUBS:
        sub = sub.strip()
        posts = fetch_posts(sub)
        limit = LIMIT_POSTS_DICT.get(sub, DEFAULT_LIMIT_POSTS)
        filtered = []

        for p in posts:
            if p.id in posted_ids or p.subreddit.display_name.lower() == TARGET_SUB.lower():
                continue
            if not match_keywords(p.title):
                continue

            if not p.is_self:
                norm_url = normalize_link(p.url)
                if norm_url in seen_links:
                    continue
                seen_links.add(norm_url)

            filtered.append(p)

        filtered = filtered[:limit]
        print(f"🔹 r/{sub}: selected {len(filtered)} posts (limit {limit})")
        for p in filtered:
            print(f"   Selected: {p.title}")
        all_posts.extend(filtered)

    recent_titles = get_recent_target_posts(hours=24)

    candidates = []
    for p in all_posts:
        orig_title = get_original_post_title(p)
        src_lang = TRANSLATE_SOURCE_LANGS.get(p.subreddit.display_name.lower())
        skip_translation = src_lang and src_lang.upper() == TRANSLATE_TARGET_LANG.upper()
        candidates.append({
            "id": p.id,
            "title": orig_title,
            "body": p.selftext if p.is_self else "",
            "source_lang": None if skip_translation else src_lang,
            "subreddit": p.subreddit.display_name
        })

    title_map = {}
    if candidates:
        print(f"🔹 Sending {len(candidates)} candidates to Gemini for translation and flair suggestion...")
        for c in candidates:
            print(f"   Candidate: {c['id']} | {c['title']} | src_lang={c['source_lang']}")
        
        result = translate_and_filter_with_gemini(
            candidates,
            recent_titles,
            target_lang=TRANSLATE_TARGET_LANG,
            flair_options=flair_options
        )
        if "error" in result:
            print(f"❌ Gemini error: {result['error']}")
        else:
            title_map = result
            print(f"🔹 Gemini returned {len(title_map)} results:")
            for post_id, entry in title_map.items():
                print(f"   {post_id}: {entry}")

    process_posts(all_posts, title_map, flairs, posted_ids, recent_titles)

    save_posted_ids(posted_ids)
    print("✅ Done")

except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
