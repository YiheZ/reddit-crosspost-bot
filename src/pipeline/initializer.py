"""Initialization step - loads state and configuration."""

from typing import Dict, List
from config import config
from reddit_client import RedditClient
from storage import GistStorage


class PipelineInitializer:
    """Handles pipeline initialization."""

    def __init__(self, reddit: RedditClient, storage: GistStorage):
        """Initialize with dependencies.
        
        Args:
            reddit: Reddit client instance
            storage: Storage handler instance
        """
        self.reddit = reddit
        self.storage = storage
        self.posted_ids: Dict = {}
        self.flairs: List = []
        self.flair_options: List[str] = []
        self.recent_titles: List[str] = []

    def initialize(self) -> tuple:
        """Initialize pipeline state.
        
        Returns:
            Tuple of (posted_ids, flairs, flair_options, recent_titles)
        """
        print("🔹 Initializing pipeline...")
        
        # Load posted IDs
        self.posted_ids = self.storage.load_posted_ids()
        print(f"🔹 Loaded {len(self.posted_ids)} previously posted IDs.")

        # Fetch flairs
        self.flairs = self.reddit.fetch_target_flairs()
        self.flair_options = [f["text"] for f in self.flairs]
        print(f"🔹 Available flairs in r/{config.target_sub}: {self.flair_options}")

        # Get recent titles
        self.recent_titles = self.reddit.get_recent_target_posts(hours=24)
        print(f"🔹 Loaded {len(self.recent_titles)} recent target posts.")

        return self.posted_ids, self.flairs, self.flair_options, self.recent_titles
