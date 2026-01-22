"""Configuration module for Reddit crosspost bot."""

import os
import json
from typing import Dict, List, Any


def load_json_env(env_name: str, default: Any) -> Any:
    """Safely load JSON from environment variable."""
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON in {env_name}, using default {default}")
        return default


class BotConfig:
    """Centralized configuration for the bot."""

    def __init__(self):
        # Reddit API credentials
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.reddit_username = os.getenv("REDDIT_USERNAME")
        self.reddit_password = os.getenv("REDDIT_PASSWORD")

        # GitHub Gist storage
        self.gist_id = os.getenv("GIST_ID")
        self.gist_pat = os.getenv("MY_GIST_PAT")

        # Source and target subreddits
        self.source_subs = [s.strip() for s in os.getenv("SOURCE_SUBS", "news").split(",")]
        self.target_sub = os.getenv("TARGET_SUB", "yoursub")

        # Content filtering
        self.include_keywords = load_json_env("INCLUDE_KEYWORDS", [])
        self.exclude_keywords = load_json_env("EXCLUDE_KEYWORDS", [])

        # Translation settings
        self.translate_target_lang = os.getenv("TRANSLATE_TARGET_LANG", "ZH")
        self.translate_source_langs = load_json_env("TRANSLATE_SOURCE_LANGS", {})

        # Fetching mode
        self.fetch_mode = os.getenv("FETCH_MODE", "popular").lower()

        # Post limits per subreddit
        self.limit_posts_dict = load_json_env("LIMIT_POSTS", {})
        self.default_limit_posts = 1

        # Retry settings
        self.max_retries = 3

        # Translation APIs
        self.deepl_api_key = os.getenv("DEEPL_API_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

        # Gemini settings
        self.gemini_model_name = "gemini-2.5-flash"
        self.debug_prompt = os.getenv("DEBUG_PROMPT", "false").lower() == "true"
        self.allow_gemini_fetch = os.getenv("ALLOW_GEMINI_FETCH", "true").lower() == "true"

    def validate(self) -> bool:
        """Validate that all required settings are configured."""
        required = [
            self.reddit_client_id,
            self.reddit_client_secret,
            self.reddit_username,
            self.reddit_password,
            self.gist_id,
            self.gist_pat,
        ]
        return all(required)

    def __repr__(self) -> str:
        return (
            f"BotConfig(target_sub={self.target_sub}, source_subs={self.source_subs}, "
            f"fetch_mode={self.fetch_mode}, target_lang={self.translate_target_lang})"
        )


# Global config instance
config = BotConfig()
