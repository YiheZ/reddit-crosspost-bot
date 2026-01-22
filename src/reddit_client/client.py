"""Main Reddit API client wrapper."""

import praw
from config import BotConfig
from .fetcher import PostFetcher
from .submitter import PostSubmitter


class RedditClient:
    """Wrapper around PRAW for Reddit API interactions."""

    def __init__(self, config: BotConfig):
        """Initialize Reddit client with credentials from config."""
        self.config = config
        self.reddit = praw.Reddit(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=f"auto-crosspost-bot by u/{config.reddit_username}",
            username=config.reddit_username,
            password=config.reddit_password,
        )
        
        # Initialize sub-components
        self.fetcher = PostFetcher(self.reddit, config)
        self.submitter = PostSubmitter(self.reddit, config)

    # Delegate fetching methods to fetcher
    def fetch_posts(self, subreddit_name: str, max_candidates: int = 500, top_limit: int = 100):
        """Fetch posts from a subreddit based on fetch mode."""
        return self.fetcher.fetch_posts(subreddit_name, max_candidates, top_limit)

    def get_recent_target_posts(self, hours: int = 24):
        """Get titles of recent posts in target subreddit."""
        return self.fetcher.get_recent_target_posts(hours)

    def fetch_target_flairs(self):
        """Fetch available flairs from target subreddit."""
        return self.fetcher.fetch_target_flairs()

    def get_deepest_original(self, post):
        """Get the deepest original submission (follows crosspost chain)."""
        return self.fetcher.get_deepest_original(post)

    # Delegate submission methods to submitter
    def submit_link(self, title: str, url: str, flair_id=None, body: str = ""):
        """Submit a link post to target subreddit."""
        return self.submitter.submit_link(title, url, flair_id, body)

    def crosspost(self, post, title: str, flair_id=None):
        """Create a crosspost in target subreddit."""
        return self.submitter.crosspost(post, title, flair_id)
