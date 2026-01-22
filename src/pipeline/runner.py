"""Main pipeline runner - orchestrates all steps."""

import sys
from typing import List, Tuple, Dict

from config import config
from reddit_client import RedditClient
from storage import GistStorage
from content import ContentFilter
from processors import CandidateBuilder
from processors.submission import PostProcessor
from core import BotConfigError

from .initializer import PipelineInitializer
from .fetcher import PostFetcher
from .translator import PostTranslator


class BotPipeline:
    """Orchestrates the complete bot workflow."""

    def __init__(self):
        """Initialize pipeline with all components."""
        if not config.validate():
            raise BotConfigError("Missing required configuration")

        # Core components
        self.reddit = RedditClient(config)
        self.storage = GistStorage(config)
        self.filter = ContentFilter(config)
        self.candidate_builder = CandidateBuilder(config)
        self.post_processor = PostProcessor(self.reddit, config)

        # Pipeline steps
        self.initializer = PipelineInitializer(self.reddit, self.storage)
        self.fetcher = PostFetcher(self.reddit, self.filter)
        self.translator = PostTranslator()

        # State
        self.flairs = []
        self.flair_options = []
        self.posted_ids = {}
        self.recent_titles = []

    def initialize(self):
        """Initialize pipeline state."""
        self.posted_ids, self.flairs, self.flair_options, self.recent_titles = (
            self.initializer.initialize()
        )

    def fetch_and_filter_posts(self) -> List:
        """Fetch posts from source subreddits and apply filters."""
        return self.fetcher.fetch_and_filter_posts(self.posted_ids)

    def prepare_candidates(self, posts: List) -> List:
        """Prepare posts as translation candidates."""
        return self.translator.prepare_candidates(
            posts, self.reddit, self.candidate_builder
        )

    def translate_candidates(self, candidates: List) -> Dict:
        """Send candidates to translation service."""
        return self.translator.translate_candidates(
            candidates, self.recent_titles, self.flair_options
        )

    def submit_posts(self, posts: List, title_map: Dict) -> Tuple[List, Dict]:
        """Submit posts to target subreddit."""
        print(f"\n🔹 Submitting posts...")
        failed, updated_ids = self.post_processor.process_and_submit(
            posts, title_map, self.flairs, self.posted_ids, self.recent_titles, retries=0
        )
        self.posted_ids = updated_ids
        return failed, updated_ids

    def save_state(self):
        """Save state to storage."""
        print("\n🔹 Saving state...")
        success = self.storage.save_posted_ids(self.posted_ids)
        if success:
            print("✅ State saved successfully")
        else:
            print("⚠️ Failed to save state")

    def run(self):
        """Execute the complete pipeline."""
        try:
            # Initialize
            self.initialize()

            # Fetch and filter
            posts = self.fetch_and_filter_posts()
            if not posts:
                print("ℹ️ No posts to process")
                return

            # Prepare candidates
            candidates = self.prepare_candidates(posts)
            if not candidates:
                print("ℹ️ No candidates after preparation")
                return

            # Translate
            title_map = self.translate_candidates(candidates)
            if not title_map:
                print("⚠️ No translations received")
                return

            # Submit
            failed, self.posted_ids = self.submit_posts(posts, title_map)

            # Save
            self.save_state()

            print("\n✅ Pipeline completed successfully")

        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
