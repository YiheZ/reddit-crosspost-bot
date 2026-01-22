"""Storage module for tracking posted content via GitHub Gist."""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, Tuple
from config import BotConfig


class GistStorage:
    """Manages persistent storage of posted IDs using GitHub Gist."""

    def __init__(self, config: BotConfig):
        """Initialize Gist storage with config."""
        self.config = config
        self.gist_api_url = f"https://api.github.com/gists/{config.gist_id}"
        self.headers = {
            "Authorization": f"token {config.gist_pat}",
            "Accept": "application/vnd.github.v3+json",
        }

    def load_posted_ids(self) -> Dict:
        """Load posted IDs from Gist, filtering out entries older than 7 days."""
        try:
            response = requests.get(self.gist_api_url, headers=self.headers)
            if response.status_code != 200:
                print(f"⚠️ Failed to load posted IDs: {response.status_code} {response.text}")
                return {}

            gist_data = response.json()
            files = gist_data.get("files", {})
            content = files.get("posted_ids.json", {}).get("content", "{}")
            data = json.loads(content)

            now_ts = int(datetime.now(timezone.utc).timestamp())
            clean_data = {}

            for pid, val in data.get("posted_ids", {}).items():
                if isinstance(val, dict):
                    ts = val.get("ts", 0)
                    url = val.get("url", "")
                else:
                    ts, url = val, ""

                # Keep entries from last 7 days
                if now_ts - ts <= 7 * 24 * 3600:
                    clean_data[pid] = {"ts": ts, "url": url}

            return clean_data
        except Exception as e:
            print(f"⚠️ Error loading posted IDs: {e}")
            return {}

    def save_posted_ids(self, posted_ids: Dict) -> bool:
        """Save posted IDs to Gist."""
        try:
            payload = {"files": {"posted_ids.json": {"content": json.dumps({"posted_ids": posted_ids}, indent=2)}}}
            response = requests.patch(self.gist_api_url, headers=self.headers, json=payload)
            if response.status_code != 200:
                print(f"⚠️ Failed to save posted IDs: {response.status_code} {response.text}")
                return False
            return True
        except Exception as e:
            print(f"⚠️ Error saving posted IDs: {e}")
            return False

    def mark_posted(self, post_id: str, post_url: str = "") -> None:
        """Mark a post as posted with current timestamp."""
        now_ts = int(datetime.now(timezone.utc).timestamp())
        # This will be used in context with loaded posted_ids
        return {"ts": now_ts, "url": post_url}
