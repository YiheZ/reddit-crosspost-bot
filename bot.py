import os
import praw
import time
import json
import requests
from datetime import datetime, timedelta

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
GITHUB_PAT = os.getenv("MY_GIST_PAT")
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

def load_posted_ids():
    try:
        response = requests.get(GIST_API_URL, headers=HEADERS)
        response.raise_for_status()
        gist_data = response.json()
        files = gist_data.get("files", {})
        posted_file = files.get("posted_ids.json", {})
        content = posted_file.get("content", "{}")
        data = json.loads(content)
        return set(data.get("posted_ids", []))
    except Exception as e:
        print(f"⚠️ Failed to load posted IDs from Gist: {e}")
        return set()

def save_posted_ids(posted_ids):
    data = {
        "posted_ids.json": {
            "content": json.dumps({"posted_ids": list(posted_ids)}, indent=2)
        }
    }
    payload = {"files": data}
    try:
        response = requests.patch(GIST_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"⚠️ Failed to save posted IDs to Gist: {e}")

# Variables from repo variables
SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")
KEYWORDS = os.getenv("KEYWORDS", "").lower().split(",")
LIMIT_POSTS = int(os.getenv("LIMIT_POSTS", "3"))
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "60"))
STATE_FILE = "last_run.json"

# Load last run time from environment or default to 0
posted_ids = load_posted_ids()

def match_keywords(title):
    if not KEYWORDS or KEYWORDS == ['']:
        return True
    title_lower = title.lower()
    return any(kw.strip() in title_lower for kw in KEYWORDS if kw.strip())

def get_top_posts_past_day(subreddit_name, limit=5):
    subreddit = reddit.subreddit(subreddit_name)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    posts = []
    for post in subreddit.new(limit=limit*3):
        post_time = datetime.utcfromtimestamp(post.created_utc)
        if post_time < one_day_ago:
            continue
        posts.append(post)
    posts.sort(key=lambda p: p.score, reverse=True)
    return posts[:limit]

for sub in SOURCE_SUBS:
    try:
        posts = get_top_posts_past_day(sub.strip(), limit=LIMIT_POSTS)
        crossposted = 0
        for post in posts:
            if post.id in posted_ids:
                continue
            if not match_keywords(post.title):
                continue
            post.crosspost(subreddit=TARGET_SUB, send_replies=False)
            print(f"✅ Crossposted from r/{sub}: {post.title}")
            posted_ids.add(post.id)
            crossposted += 1
            if crossposted >= LIMIT_POSTS:
                break
    except Exception as e:
        print(f"❌ Error processing r/{sub}: {e}")

save_posted_ids(posted_ids)

print("✅ Done")
