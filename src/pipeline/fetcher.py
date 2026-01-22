"""Fetcher step - retrieves and filters posts from source subreddits."""

from typing import List, Set, Dict
from config import config
from reddit_client import RedditClient
from content import ContentFilter, extract_saved_urls


class PostFetcher:
    """Handles fetching and initial filtering of posts."""

    def __init__(self, reddit: RedditClient, content_filter: ContentFilter):
        """Initialize with dependencies.
        
        Args:
            reddit: Reddit client instance
            content_filter: Content filter instance
        """
        self.reddit = reddit
        self.filter = content_filter

    def fetch_and_filter_posts(self, posted_ids: Dict) -> List:
        """Fetch posts from source subreddits and apply filters.
        
        Args:
            posted_ids: Dictionary of previously posted IDs
            
        Returns:
            List of filtered posts
        """
        print("\n🔹 Fetching and filtering posts...")
        all_posts = []
        seen_links: Set[str] = set()
        saved_urls = extract_saved_urls(posted_ids)

        for sub in config.source_subs:
            sub = sub.strip()
            posts = self.reddit.fetch_posts(sub)
            limit = config.limit_posts_dict.get(sub, config.default_limit_posts)
            filtered = []

            for p in posts:
                # Skip if already posted or in target sub
                if p.id in posted_ids or p.subreddit.display_name.lower() == config.target_sub.lower():
                    continue

                # Skip if doesn't match keywords
                if not self.filter.match_keywords(p.title):
                    continue

                # Skip duplicates
                if not p.is_self:
                    norm_url = self.filter.normalize_link(p.url)
                    if norm_url in seen_links or norm_url in saved_urls:
                        continue
                    seen_links.add(norm_url)

                filtered.append(p)

            filtered = filtered[:limit]
            print(f"🔹 r/{sub}: selected {len(filtered)} posts (limit {limit})")
            for p in filtered:
                print(f"   Selected: {p.title}")
            all_posts.extend(filtered)

        return all_posts
