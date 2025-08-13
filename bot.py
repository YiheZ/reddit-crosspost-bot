import os
import praw
import time
import json
from datetime import datetime, timedelta

# Reddit API setup
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="auto-crosspost-bot by u/{}".format(os.getenv("REDDIT_USERNAME")),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

# Variables from repository settings
SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")
KEYWORDS = os.getenv("KEYWORDS", "").lower().split(",")
LIMIT_POSTS = int(os.getenv("LIMIT_POSTS", "3"))  # Will still limit how many posts to try crossposting per sub
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "60"))
STATE_FILE = "last_run.json"

# Load last run time and posted IDs to avoid duplicates
last_run_time = 0
posted_ids = set()
try:
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
        last_run_time = state.get("last_run", 0)
        posted_ids = set(state.get("posted_ids", []))
except FileNotFoundError:
    pass

now = time.time()
if now - last_run_time < INTERVAL_MIN * 60:
    print(f"⏳ Last run was less than {INTERVAL_MIN} minutes ago, skipping execution.")
    exit(0)

def match_keywords(title):
    if not KEYWORDS or KEYWORDS == ['']:
        return True
    title_lower = title.lower()
    return any(kw.strip() in title_lower for kw in KEYWORDS if kw.strip())

def get_top_posts_past_day(subreddit_name, limit=5):
    """Fetch posts from past day, sorted by score descending"""
    subreddit = reddit.subreddit(subreddit_name)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    posts = []
    for post in subreddit.new(limit=limit*3):  # get more to filter by time
        post_time = datetime.utcfromtimestamp(post.created_utc)
        if post_time < one_day_ago:
            continue
        posts.append(post)
    # Sort by score descending
    posts.sort(key=lambda p: p.score, reverse=True)
    return posts[:limit]

for sub in SOURCE_SUBS:
    try:
        posts = get_top_posts_past_day(sub.strip(), limit=LIMIT_POSTS)
        crossposted_count = 0
        for post in posts:
            if post.id in posted_ids:
                # Already crossposted, skip
                continue
            if not match_keywords(post.title):
                continue
            post.crosspost(subreddit=TARGET_SUB, send_replies=False)
            print(f"✅ Crossposted from r/{sub}: {post.title}")
            posted_ids.add(post.id)
            crossposted_count += 1
            if crossposted_count >= LIMIT_POSTS:
                break
    except Exception as e:
        print(f"❌ Error processing r/{sub}: {e}")

# Save state with last run time and posted ids
with open(STATE_FILE, "w") as f:
    json.dump({"last_run": now, "posted_ids": list(posted_ids)}, f)

print("✅ Done")
