import os
import praw
import time

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="auto-crosspost-bot by u/{}".format(os.getenv("REDDIT_USERNAME")),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

SOURCE_SUBS = os.getenv("SOURCE_SUBS", "news").split(",")
TARGET_SUB = os.getenv("TARGET_SUB", "yoursub")
KEYWORDS = os.getenv("KEYWORDS", "").lower().split(",")

posted_ids = set()

def match_keywords(title):
    if not KEYWORDS or KEYWORDS == ['']:
        return True
    title_lower = title.lower()
    return any(kw.strip() in title_lower for kw in KEYWORDS if kw.strip())

for sub in SOURCE_SUBS:
    try:
        for submission in reddit.subreddit(sub.strip()).new(limit=5):
            if submission.id not in posted_ids and match_keywords(submission.title):
                submission.crosspost(subreddit=TARGET_SUB, send_replies=False)
                print(f"✅ Crossposted from r/{sub}: {submission.title}")
                posted_ids.add(submission.id)
    except Exception as e:
        print(f"❌ Error processing r/{sub}: {e}")

print("✅ Done")
