import os
import praw
import time
import json

# Reddit API setup
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="auto-crosspost-bot by u/{}".format(os.getenv("REDDIT_USERNAME")),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

# Variables from repository settings
SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")  # Source subreddits
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")            # Target subreddit
KEYWORDS = os.getenv("KEYWORDS", "").lower().split(",")    # Keyword filter (optional)
LIMIT_POSTS = int(os.getenv("LIMIT_POSTS", "3"))            # Number of posts each run
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "60"))         # Run interval in minutes
STATE_FILE = "last_run.json"

# Check last run time
last_run_time = 0
try:
    with open(STATE_FILE, "r") as f:
        last_run_time = json.load(f).get("last_run", 0)
except FileNotFoundError:
    pass

now = time.time()
if now - last_run_time < INTERVAL_MIN * 60:
    print(f"⏳ Last run was less than {INTERVAL_MIN} minutes ago, skipping execution.")
    exit(0)

posted_ids = set()

def match_keywords(title):
    """Check if post title contains any of the keywords."""
    if not KEYWORDS or KEYWORDS == ['']:
        return True
    title_lower = title.lower()
    return any(kw.strip() in title_lower for kw in KEYWORDS if kw.strip())

for sub in SOURCE_SUBS:
    try:
        for submission in reddit.subreddit(sub.strip()).new(limit=LIMIT_POSTS):
            if submission.id not in posted_ids and match_keywords(submission.title):
                submission.crosspost(subreddit=TARGET_SUB, send_replies=False)
                print(f"✅ Crossposted from r/{sub}: {submission.title}")
                posted_ids.add(submission.id)
    except Exception as e:
        print(f"❌ Error processing r/{sub}: {e}")

# Save last run time
with open(STATE_FILE, "w") as f:
    json.dump({"last_run": now}, f)

print("✅ Done")
