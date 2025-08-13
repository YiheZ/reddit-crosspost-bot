import os
import praw
import json
import requests
from datetime import datetime, timedelta, timezone
import sys

# Reddit API setup
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="auto-crosspost-bot by u/{}".format(os.getenv("REDDIT_USERNAME")),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

# GitHub Gist API info from env
GIST_ID = os.getenv("GIST_ID")
MY_GIST_PAT = os.getenv("MY_GIST_PAT")
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {MY_GIST_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

def load_posted_ids():
    response = requests.get(GIST_API_URL, headers=HEADERS)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to load posted IDs from Gist: {response.status_code} {response.text}")
    gist_data = response.json()
    files = gist_data.get("files", {})
    posted_file = files.get("posted_ids.json", {})
    content = posted_file.get("content", "{}")
    data = json.loads(content)
    return set(data.get("posted_ids", []))

def save_posted_ids(posted_ids):
    data = {
        "posted_ids.json": {
            "content": json.dumps({"posted_ids": list(posted_ids)}, indent=2)
        }
    }
    payload = {"files": data}
    response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to save posted IDs to Gist: {response.status_code} {response.text}")

# Read env vars
SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")
KEYWORDS = os.getenv("KEYWORDS", "").lower().split(",")
LIMIT_POSTS = int(os.getenv("LIMIT_POSTS", "3"))
CROSSPOST_FLAIR_ID = os.getenv("CROSSPOST_FLAIR_ID")  # flair template ID for the crossposts

posted_ids = load_posted_ids()

def match_keywords(title):
    if not KEYWORDS or KEYWORDS == ['']:
        return True
    title_lower = title.lower()
    return any(kw.strip() in title_lower for kw in KEYWORDS if kw.strip())

def get_top_posts_past_day(subreddit_name, max_candidates=500, top_limit=100):
    subreddit = reddit.subreddit(subreddit_name)
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    posts = []
    for post in subreddit.new(limit=max_candidates):
        post_time = datetime.fromtimestamp(post.created_utc, timezone.utc)
        if post_time < one_day_ago:
            continue
        posts.append(post)
    posts.sort(key=lambda p: p.score, reverse=True)
    return posts[:top_limit]

try:
    for sub in SOURCE_SUBS:
        posts = get_top_posts_past_day(sub.strip(), max_candidates=500, top_limit=100)
        crossposted = 0
        for post in posts:
            if post.id in posted_ids:
                # Already crossposted, skip but don't count toward limit
                continue
            if not match_keywords(post.title):
                continue

            crosspost_kwargs = {"subreddit": TARGET_SUB, "send_replies": False}
            if CROSSPOST_FLAIR_ID:
                crosspost_kwargs["flair_id"] = CROSSPOST_FLAIR_ID

            post.crosspost(**crosspost_kwargs)

            print(f"✅ Crossposted from r/{sub}: {post.title}")
            posted_ids.add(post.id)
            crossposted += 1
            if crossposted >= LIMIT_POSTS:
                break

    save_posted_ids(posted_ids)
    print("✅ Done")
except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
