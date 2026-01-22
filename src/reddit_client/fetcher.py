"""Post fetcher - handles fetching posts and metadata from Reddit."""

from typing import List
from datetime import datetime, timedelta, timezone


class PostFetcher:
    """Handles fetching posts, flairs, and metadata from Reddit."""

    def __init__(self, reddit, config):
        """Initialize with PRAW instance and config.
        
        Args:
            reddit: PRAW Reddit instance
            config: BotConfig instance
        """
        self.reddit = reddit
        self.config = config

    def fetch_posts(self, subreddit_name: str, max_candidates: int = 500, top_limit: int = 100) -> List:
        """Fetch posts from a subreddit based on fetch mode.
        
        Args:
            subreddit_name: Name of subreddit to fetch from
            max_candidates: Maximum number of posts to consider
            top_limit: Limit for number of posts to return
            
        Returns:
            List of PRAW submission objects
        """
        subreddit = self.reddit.subreddit(subreddit_name)
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        # Fetch recent posts (last 24 hours)
        posts = [
            p
            for p in subreddit.new(limit=max_candidates)
            if datetime.fromtimestamp(p.created_utc, timezone.utc) >= one_day_ago
        ]

        # Sort based on mode
        if self.config.fetch_mode == "latest":
            posts.sort(key=lambda p: p.created_utc, reverse=True)
        else:  # popular mode
            posts.sort(key=lambda p: p.score, reverse=True)

        return posts[:top_limit]

    def get_recent_target_posts(self, hours: int = 24) -> List[str]:
        """Get titles of recent posts in target subreddit.
        
        Args:
            hours: How many hours back to fetch
            
        Returns:
            List of post titles
        """
        subreddit = self.reddit.subreddit(self.config.target_sub)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        posts = [
            p
            for p in subreddit.new(limit=200)
            if datetime.fromtimestamp(p.created_utc, timezone.utc) >= cutoff
        ]
        
        return [p.title for p in posts]

    def fetch_target_flairs(self) -> List[dict]:
        """Fetch available flairs from target subreddit.
        
        Returns:
            List of flair dictionaries with 'text' and 'id' keys
        """
        subreddit = self.reddit.subreddit(self.config.target_sub)
        flairs = []
        
        for f in subreddit.flair.link_templates:
            if f["text"]:
                flairs.append({"text": f["text"], "id": f["id"]})
                
        return flairs

    def get_deepest_original(self, post):
        """Get the deepest original submission (follows crosspost chain).
        
        Args:
            post: PRAW submission object
            
        Returns:
            Original PRAW submission object
        """
        while hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
            orig_id = post.crosspost_parent_list[0]["id"]
            post = self.reddit.submission(id=orig_id)
            
        return post
