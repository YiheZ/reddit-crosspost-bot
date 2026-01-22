"""Post processor - handles submission and retry logic."""

import time
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from models import TranslatedPost, SubmissionResult, PostedRecord
from core.constants import MIN_POST_DELAY, MAX_POST_DELAY
from content import get_current_timestamp
from core.exceptions import SubmissionError


class PostProcessor:
    """Processes and submits posts to target subreddit."""

    def __init__(self, reddit_client, config):
        """Initialize processor."""
        self.reddit = reddit_client
        self.config = config

    def process_and_submit(
        self,
        posts: List,
        title_map: Dict[str, TranslatedPost],
        flairs: List[Dict],
        posted_ids: Dict,
        recent_titles: List[str],
        retries: int = 0,
    ) -> Tuple[List, Dict]:
        """
        Process posts and submit them.
        Returns (failed_posts, updated_posted_ids)
        """
        failed = []
        now_ts = get_current_timestamp()

        for post in posts:
            try:
                # Skip if already posted
                if post.id in posted_ids:
                    continue

                # Get translation data
                entry = title_map.get(post.id, {})
                if isinstance(entry, TranslatedPost):
                    translated = entry
                else:
                    translated = TranslatedPost(**entry) if entry else None

                if not translated:
                    print(f"⚠️ No translation data for {post.id}")
                    failed.append(post)
                    continue

                # Check if intentionally skipped
                if translated.skip:
                    print(f"⏭ Intentionally skipped {post.id}")
                    posted_ids[post.id] = {"ts": now_ts, "url": post.url if not post.is_self else ""}
                    continue

                # Validate required data
                if not translated.title_translated or not translated.suggested_flair:
                    print(f"⚠️ Missing translation or flair for {post.id} – will retry")
                    failed.append(post)
                    continue

                # Find flair ID
                flair_id = self._find_flair_id(translated.suggested_flair, flairs)
                if not flair_id:
                    print(f"⚠️ Flair '{translated.suggested_flair}' not found – will retry")
                    failed.append(post)
                    continue

                # Submit post
                result = self._submit_post(post, translated, flair_id)
                if result.success:
                    print(f"{result}")
                    posted_ids[post.id] = {"ts": now_ts, "url": post.url if not post.is_self else ""}
                    if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
                        posted_ids[post.crosspost_parent_list[0]["id"]] = {
                            "ts": now_ts,
                            "url": post.url if not post.is_self else "",
                        }
                else:
                    print(f"{result}")
                    failed.append(post)

                # Delay between submissions
                time.sleep(random.randint(MIN_POST_DELAY, MAX_POST_DELAY))

            except Exception as e:
                print(f"⚠️ Error processing post {post.id}: {e}")
                failed.append(post)

        # Handle retries
        if failed and retries < self.config.max_retries:
            print(f"🔁 Retrying {len(failed)} failed posts (attempt {retries+1}/{self.config.max_retries})...")
            # Retry logic would call this function recursively
            # This is left to the caller for flexibility

        elif failed:
            print(f"❌ Max retries reached for {len(failed)} posts")

        return failed, posted_ids

    def _find_flair_id(self, flair_text: str, flairs: List[Dict]) -> Optional[str]:
        """Find flair ID by text."""
        for flair in flairs:
            if flair_text in flair.get("text", ""):
                return flair.get("id")
        return None

    def _submit_post(
        self, post, translated: TranslatedPost, flair_id: str
    ) -> SubmissionResult:
        """Submit a single post."""
        try:
            if not post.is_self:
                # Submit external link
                reddit_id = self.reddit.submit_link(
                    title=translated.title_translated,
                    url=post.url,
                    flair_id=flair_id,
                    body=translated.content_translated,
                )
                return SubmissionResult(
                    success=True,
                    post_id=post.id,
                    reddit_id=reddit_id,
                    submission_type="link",
                )
            else:
                # Crosspost for self posts
                reddit_id = self.reddit.crosspost(
                    post, title=translated.title_translated, flair_id=flair_id
                )
                return SubmissionResult(
                    success=True,
                    post_id=post.id,
                    reddit_id=reddit_id,
                    submission_type="crosspost",
                )
        except Exception as e:
            return SubmissionResult(
                success=False,
                post_id=post.id,
                error=str(e),
            )
