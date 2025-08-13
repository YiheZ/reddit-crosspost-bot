# Reddit Auto Crosspost Bot

This bot automatically crossposts the most popular posts from one or more source subreddits to a target subreddit, based on keywords and a daily popularity ranking.

It stores the IDs of already crossposted posts in a GitHub Gist to avoid reposting duplicates.

---

## Features
- Pulls posts from multiple source subreddits
- Filters posts by keywords (optional)
- Sorts by **popularity** in the past 24 hours
- Limits the number of posts per run and per source subreddit
- Adds an optional flair to crossposts
- Stores posted IDs in a GitHub Gist so duplicates are avoided across runs
- Configurable via environment variables

---

## Requirements
- Python 3.7+
- Reddit API credentials (via [Reddit App](https://www.reddit.com/prefs/apps))
- GitHub account with a Gist and a Personal Access Token (PAT) with `gist` permission

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/reddit-auto-crosspost.git
cd reddit-auto-crosspost
```

### 2. Install dependencies
```bash
pip install praw requests
```

### 3. Create a Reddit App
1. Go to [Reddit Apps](https://www.reddit.com/prefs/apps)
2. Click **create app**
3. Choose **script**
4. Fill in `redirect_uri` as `http://localhost`
5. Save and note your `client_id` and `client_secret`

### 4. Create a Gist
1. Go to [Gists](https://gist.github.com/)
2. Create a **Secret Gist**
3. Add a file named `posted_ids.json` with the following content:
```json
{
  "posted_ids": []
}
```
4. Save the Gist and note its **Gist ID** (last part of the URL).

### 5. Create a Personal Access Token (PAT)
1. Go to [GitHub PAT Settings](https://github.com/settings/tokens)
2. Generate a token with **gist** permission
3. Copy the token — you will use it as `MY_GIST_PAT`.

---

## Environment Variables

| Variable            | Description |
|---------------------|-------------|
| `REDDIT_CLIENT_ID`  | Your Reddit App client ID |
| `REDDIT_CLIENT_SECRET` | Your Reddit App client secret |
| `REDDIT_USERNAME`   | Your Reddit username |
| `REDDIT_PASSWORD`   | Your Reddit password |
| `SOURCE_SUBS`       | Comma-separated source subreddits (e.g., `news,worldnews`) |
| `TARGET_SUB`        | Target subreddit to crosspost to |
| `KEYWORDS`          | Comma-separated keywords to match in titles (leave empty for all posts) |
| `LIMIT_POSTS`       | Maximum posts to crosspost per subreddit per run |
| `CROSSPOST_FLAIR_ID`| Optional flair template ID for the crossposts |
| `GIST_ID`           | Your Gist ID containing `posted_ids.json` |
| `MY_GIST_PAT`       | GitHub Personal Access Token with `gist` scope |

Example `.env` file:
```env
REDDIT_CLIENT_ID=abc123
REDDIT_CLIENT_SECRET=xyz456
REDDIT_USERNAME=yourusername
REDDIT_PASSWORD=yourpassword
SOURCE_SUBS=news,worldnews
TARGET_SUB=mysubreddit
KEYWORDS=china,technology
LIMIT_POSTS=3
CROSSPOST_FLAIR_ID=flairid123
GIST_ID=abcd1234efgh5678ijkl
MY_GIST_PAT=ghp_YourPATTokenHere
```

---

## Usage

Run the bot manually:
```bash
python bot.py
```

Or set it up as a cron job / GitHub Actions workflow.

---

## Notes
- Ensure your Gist contains a file named `posted_ids.json` with:
```json
{
  "posted_ids": []
}
```
- Your personal access token must have the `gist` permission.
- The bot uses the last 24 hours of posts and sorts them by Reddit score.

---

## License
MIT License
