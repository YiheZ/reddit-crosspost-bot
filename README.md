# Reddit Auto Crosspost Bot

This is a Python bot that automatically crossposts the most **popular** Reddit posts from one or more source subreddits to a target subreddit.  
It uses:
- [PRAW](https://praw.readthedocs.io/en/stable/) for Reddit API access
- GitHub Gist for tracking already posted IDs (to prevent duplicates)
- GitHub Actions for scheduled automation

## Features
✅ Select top posts from the past day (ranked by score, not by newest)  
✅ Skip posts already crossposted (tracked in Gist)  
✅ Supports multiple source subreddits  
✅ Keyword filtering  
✅ Optional crosspost flair ID  
✅ Limit posts per run  
✅ Runs automatically via GitHub Actions schedule  

---

## 1. Prerequisites

- A Reddit account
- A Reddit API application (script type)
- A GitHub account with:
  - Repository for hosting the bot
  - Personal Access Token (PAT) with `gist` scope
  - A Gist (for storing `posted_ids.json`)

---

## 2. Setup Reddit API

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps).
2. Click **Create another app**.
3. Set:
   - **Name:** `auto-crosspost-bot`
   - **Type:** `script`
   - **Redirect URI:** `http://localhost`
4. Save and note:
   - **client_id** (under the app name)
   - **client_secret**
   - Your Reddit username & password

---

## 3. Setup Gist for posted IDs

1. Go to [Gist](https://gist.github.com/).
2. Create a **public** or **secret** Gist named `posted_ids.json` with contents:

   ```json
   {
     "posted_ids": []
   }
