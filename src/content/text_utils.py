"""Text and string manipulation utilities."""


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length.
    
    Args:
        s: String to truncate
        max_length: Maximum length including suffix
        suffix: String to append when truncating
        
    Returns:
        Truncated string with suffix if needed
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix
