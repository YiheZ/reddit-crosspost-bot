"""Content filtering for Reddit posts."""

import re
from typing import List
from config import BotConfig
from .url_utils import normalize_link


class ContentFilter:
    """Filters and processes Reddit content based on keywords and rules."""

    def __init__(self, config: BotConfig):
        """Initialize content filter with config.
        
        Args:
            config: Bot configuration instance
        """
        self.config = config

    def match_keywords(self, title: str) -> bool:
        """Check if title matches include/exclude keywords.
        
        Args:
            title: Post title to check
            
        Returns:
            True if title passes keyword filters
        """
        title_lower = title.lower()

        # Exclude keywords first
        if any(kw.lower() in title_lower for kw in self.config.exclude_keywords if kw):
            return False

        # Include keywords: match exact words
        if self.config.include_keywords:
            pattern = (
                r"\b(?:"
                + "|".join(re.escape(kw.lower()) for kw in self.config.include_keywords if kw)
                + r")\b"
            )
            return bool(re.search(pattern, title_lower))

        return True

    def is_external_link(self, post) -> bool:
        """Check if post contains an external link.
        
        Args:
            post: Reddit submission object
            
        Returns:
            True if post links to external content
        """
        if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
            original_post = post.crosspost_parent_list[0]
            if original_post.get("is_self", False):
                return False
            url_to_check = original_post.get("url", "")
        else:
            if post.is_self:
                return False
            url_to_check = post.url

        if url_to_check.startswith("/r/"):
            return False

        internal_domains = ["reddit.com", "i.redd.it", "v.redd.it", "redditmedia.com"]
        return not any(d in url_to_check for d in internal_domains)

    def get_original_post_title(self, post) -> str:
        """Get title from original post (handles crossposts).
        
        Args:
            post: Reddit submission object
            
        Returns:
            Original post title
        """
        if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
            return post.crosspost_parent_list[0]["title"]
        return post.title

    def normalize_link(self, url: str) -> str:
        """Normalize URL for comparison.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        return normalize_link(url)

    def deduplicate_posts(self, posts: List, seen_links: set, saved_urls: set) -> List:
        """Filter out duplicate posts based on IDs and URLs.
        
        Args:
            posts: List of Reddit submission objects
            seen_links: Set of already seen URLs
            saved_urls: Set of previously posted URLs
            
        Returns:
            Filtered list of posts without duplicates
        """
        filtered = []
        for p in posts:
            if not p.is_self:
                norm_url = self.normalize_link(p.url)
                if norm_url in seen_links or norm_url in saved_urls:
                    continue
                seen_links.add(norm_url)
            filtered.append(p)
        return filtered

    def prepare_candidates(self, posts: List) -> List[dict]:
        """Prepare posts as translation candidates.
        
        Args:
            posts: List of Reddit submission objects
            
        Returns:
            List of candidate dictionaries ready for translation
        """
        candidates = []
        for p in posts:
            candidates.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "body": p.selftext if p.is_self else "",
                    "url": p.url if not p.is_self else "",
                    "source_lang": None,
                    "subreddit": p.subreddit.display_name,
                    "skip_translation": False,
                }
            )
        return candidates
