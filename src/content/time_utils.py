"""Time and date utilities."""

from datetime import datetime, timezone


def get_current_timestamp() -> int:
    """Get current Unix timestamp.
    
    Returns:
        Current time as Unix timestamp (seconds since epoch)
    """
    return int(datetime.now(timezone.utc).timestamp())
