
# Reddit Auto Crosspost Bot

This bot automatically crossposts the most popular posts from one or more source subreddits to a target subreddit, based on keywords and a daily popularity ranking. It can optionally translate post titles and supports force-submitting instead of crossposting for certain subreddits.

Posted IDs are stored in a GitHub Gist to avoid reposting duplicates.

---

## Features

- Pulls posts from multiple source subreddits
- Filters posts by keywords (optional)
- Sorts by **popularity** in the past 24 hours
- Limits the number of posts per run and per source subreddit
- Adds an optional flair to crossposts
- Optional title translation using DeepL API
- Supports force-submitting certain subreddits instead of crossposting
- Stores posted IDs in a GitHub Gist to avoid duplicates
- Configurable via environment variables

---

## Requirements

- Python 3.7+
- Reddit API credentials ([Reddit App](https://www.reddit.com/prefs/apps))
- GitHub account with a Gist and Personal Access Token (PAT) with `gist` permission
- Optional DeepL API key for translation

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

### 5. Create a GitHub PAT
1. Go to [GitHub PAT Settings](https://github.com/settings/tokens)
2. Generate a token with **gist** permission
3. Copy the token — you will use it as `MY_GIST_PAT`.

---

## Environment Variables

| Variable                  | Description |
|----------------------------|-------------|
| `REDDIT_CLIENT_ID`         | Your Reddit App client ID |
| `REDDIT_CLIENT_SECRET`     | Your Reddit App client secret |
| `REDDIT_USERNAME`          | Your Reddit username |
| `REDDIT_PASSWORD`          | Your Reddit password |
| `SOURCE_SUBS`              | Comma-separated source subreddits (e.g., `news,worldnews`) |
| `TRANSLATE_SUBS`           | Comma-separated source subs that should be translated (e.g., `worldnews,technology`) |
| `FORCE_SUBMIT_SUBS`        | Comma-separated subs to submit instead of crosspost (e.g., `news`) |
| `TARGET_SUB`               | Target subreddit to crosspost/submit to |
| `KEYWORDS`                 | Comma-separated keywords to match in titles (leave empty for all posts) |
| `LIMIT_POSTS`              | JSON mapping of subreddit to max posts per run (e.g., `'{"worldnews":3,"technology":5}'`). Defaults to 5 for any sub not listed. |
| `CROSSPOST_FLAIR_ID`       | Optional flair template ID for the crossposts |
| `GIST_ID`                  | Your Gist ID containing `posted_ids.json` |
| `MY_GIST_PAT`              | GitHub Personal Access Token with `gist` scope |
| `TRANSLATE_TARGET_LANG`    | Target language code for translation (default `ZH`) |
| `TRANSLATE_SOURCE_LANGS`   | JSON mapping of source sub to language code (e.g., `'{"worldnews":"EN","Portuguese":"PT","technology":"EN"}'`) |
| `INTERVAL_MIN`             | (Optional) Interval in minutes if running periodically |

Example `.env` file:

```env
REDDIT_CLIENT_ID=abc123
REDDIT_CLIENT_SECRET=xyz456
REDDIT_USERNAME=yourusername
REDDIT_PASSWORD=yourpassword
SOURCE_SUBS=worldnews,technology,china_irl
TRANSLATE_SUBS=worldnews,technology
FORCE_SUBMIT_SUBS=worldnews
TARGET_SUB=yoursub
KEYWORDS=technology,AI
LIMIT_POSTS={"worldnews":3,"technology":5}
CROSSPOST_FLAIR_ID=flairid123
GIST_ID=abcd1234efgh5678ijkl
MY_GIST_PAT=ghp_YourPATTokenHere
TRANSLATE_TARGET_LANG=ZH
TRANSLATE_SOURCE_LANGS={"worldnews":"EN","Portuguese":"PT","technology":"EN"}
INTERVAL_MIN=30
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
- Translation uses the DeepL API (free tier available). If a subreddit is in `TRANSLATE_SUBS`, its posts will be translated before crossposting/submitting.
- Subreddits in `FORCE_SUBMIT_SUBS` will use `submit()` instead of `crosspost()`.

---

## License

MIT License
