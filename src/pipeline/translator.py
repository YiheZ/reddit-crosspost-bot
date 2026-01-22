"""Translator step - handles translation of posts."""

from typing import List, Dict
from config import config
from translation import translate_and_filter_with_gemini


class PostTranslator:
    """Handles translation of post candidates."""

    def __init__(self):
        """Initialize translator."""
        pass

    def prepare_candidates(self, posts: List, reddit_client, candidate_builder) -> List:
        """Prepare posts as translation candidates.
        
        Args:
            posts: List of posts to prepare
            reddit_client: Reddit client for fetching originals
            candidate_builder: Builder for creating candidates
            
        Returns:
            List of prepared candidates
        """
        print(f"\n🔹 Preparing {len(posts)} candidates for translation...")
        candidates = []
        for p in posts:
            orig_post = reddit_client.get_deepest_original(p)
            candidate = candidate_builder.build_candidates([orig_post])[0]
            candidates.append(candidate)
        return candidates

    def translate_candidates(self, candidates: List, recent_titles: List[str], 
                           flair_options: List[str]) -> Dict:
        """Send candidates to translation service.
        
        Args:
            candidates: List of candidates to translate
            recent_titles: Recent post titles for duplicate detection
            flair_options: Available flair options
            
        Returns:
            Dictionary mapping post IDs to translation results
        """
        if not candidates:
            return {}

        print(f"🔹 Sending {len(candidates)} candidates to Gemini...")
        for c in candidates:
            print(f"   - {c.id}: {c.title} (r/{c.subreddit})")

        result = translate_and_filter_with_gemini(
            [c.to_dict() for c in candidates],
            recent_titles,
            target_lang=config.translate_target_lang,
            flair_options=flair_options,
        )

        if "error" in result:
            print(f"❌ Gemini error: {result['error']}")
            return {}

        print(f"🔹 Gemini returned {len(result)} translations:")
        for post_id, entry in result.items():
            print(f"   {post_id}: {entry.get('title_translated', 'N/A')[:60]}")

        return result
