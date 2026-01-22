"""URL utilities for handling and normalizing URLs."""

from typing import List, Set, Dict, Any
from urllib.parse import urlparse, urlunparse


def normalize_link(url: str) -> str:
    """Normalize URL for comparison.
    
    Converts URLs to a canonical form by:
    - Lowercasing the domain
    - Removing trailing slashes from path
    - Removing query params and fragments
    
    Args:
        url: URL string to normalize
        
    Returns:
        Normalized URL string
    """
    if not url:
        return url
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    normalized = urlunparse((parsed.scheme, netloc, path, "", "", ""))
    return normalized


def deduplicate_urls(urls: List[str]) -> Set[str]:
    """Normalize and deduplicate a list of URLs.
    
    Args:
        urls: List of URL strings
        
    Returns:
        Set of normalized unique URLs
    """
    return {normalize_link(url) for url in urls if url}


def extract_saved_urls(posted_ids: Dict[str, Dict[str, Any]]) -> Set[str]:
    """Extract and normalize all saved URLs from posted IDs.
    
    Args:
        posted_ids: Dictionary mapping post IDs to metadata containing URLs
        
    Returns:
        Set of normalized URLs from posted history
    """
    urls = set()
    for entry in posted_ids.values():
        if isinstance(entry, dict) and entry.get("url"):
            urls.add(normalize_link(entry.get("url", "")))
    return urls


def is_internal_reddit_link(url: str, internal_domains: List[str]) -> bool:
    """Check if URL is internal to Reddit.
    
    Args:
        url: URL to check
        internal_domains: List of Reddit-owned domains
        
    Returns:
        True if URL is internal to Reddit
    """
    if url.startswith("/r/"):
        return True
    return any(domain in url for domain in internal_domains)
