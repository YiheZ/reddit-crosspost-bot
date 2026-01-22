"""Content filtering and utilities module.

This module provides content filtering, URL utilities, time utilities,
text utilities, and dictionary utilities for the bot.
"""

# Import from submodules
from .filter import ContentFilter
from .url_utils import (
    normalize_link,
    deduplicate_urls,
    extract_saved_urls,
    is_internal_reddit_link,
)
from .time_utils import get_current_timestamp
from .text_utils import truncate_string
from .dict_utils import safe_get_nested, merge_dicts

__all__ = [
    # Main filter class
    "ContentFilter",
    # URL utilities
    "normalize_link",
    "deduplicate_urls",
    "extract_saved_urls",
    "is_internal_reddit_link",
    # Time utilities
    "get_current_timestamp",
    # Text utilities
    "truncate_string",
    # Dict utilities
    "safe_get_nested",
    "merge_dicts",
]
