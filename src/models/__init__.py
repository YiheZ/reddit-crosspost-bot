"""Data models for the bot."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class PostCandidate:
    """Represents a post candidate for translation."""
    id: str
    title: str
    subreddit: str
    source_lang: Optional[str] = None
    body: str = ""
    url: str = ""
    skip_translation: bool = False
    url_content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "url": self.url,
            "source_lang": self.source_lang,
            "subreddit": self.subreddit,
            "skip_translation": self.skip_translation,
            "url_content": self.url_content,
        }


@dataclass
class TranslatedPost:
    """Represents a post after translation."""
    id: str
    title_translated: str
    skip: bool = False
    suggested_flair: Optional[str] = None
    content_translated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title_translated": self.title_translated,
            "skip": self.skip,
            "suggested_flair": self.suggested_flair,
            "content_translated": self.content_translated,
        }


@dataclass
class PostedRecord:
    """Record of a posted item."""
    post_id: str
    timestamp: int
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {"ts": self.timestamp, "url": self.url}


@dataclass
class Flair:
    """Reddit flair template."""
    text: str
    id: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {"text": self.text, "id": self.id}


@dataclass
class SubmissionResult:
    """Result of post submission."""
    success: bool
    post_id: str
    reddit_id: Optional[str] = None
    error: Optional[str] = None
    submission_type: str = "link"  # "link" or "crosspost"

    def __str__(self) -> str:
        if self.success:
            return f"✅ {self.submission_type.capitalize()} submitted (ID: {self.reddit_id})"
        return f"❌ Failed: {self.error}"
