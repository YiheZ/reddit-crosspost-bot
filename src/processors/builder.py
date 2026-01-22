"""Candidate builder - prepares posts for translation."""

from typing import List, Dict, Any
from models import PostCandidate
from config import config


class CandidateBuilder:
    """Builds translation candidates from Reddit posts."""

    def __init__(self, config_obj):
        """Initialize with config."""
        self.config = config_obj

    def build_candidates(self, posts: List) -> List[PostCandidate]:
        """Convert Reddit posts to candidates."""
        candidates = []
        for post in posts:
            candidate = self._build_candidate(post)
            candidates.append(candidate)
        return candidates

    def _build_candidate(self, post) -> PostCandidate:
        """Build a single candidate from a post."""
        src_lang = self.config.translate_source_langs.get(
            post.subreddit.display_name.lower()
        )
        skip_translation = (
            src_lang and src_lang.upper() == self.config.translate_target_lang.upper()
        )

        return PostCandidate(
            id=post.id,
            title=post.title,
            subreddit=post.subreddit.display_name,
            source_lang=src_lang,
            body=post.selftext if post.is_self else "",
            url=post.url if not post.is_self else "",
            skip_translation=skip_translation,
        )

    def add_url_content(
        self, candidates: List[PostCandidate], url_contents: Dict[str, str]
    ) -> List[PostCandidate]:
        """Add fetched URL content to candidates."""
        for candidate in candidates:
            if candidate.id in url_contents:
                candidate.url_content = url_contents[candidate.id]
        return candidates

    def filter_by_ids(
        self, candidates: List[PostCandidate], exclude_ids: set
    ) -> List[PostCandidate]:
        """Filter out candidates by IDs."""
        return [c for c in candidates if c.id not in exclude_ids]
