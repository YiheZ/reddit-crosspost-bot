"""Custom exceptions for the bot."""


class BotConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class RedditAPIError(Exception):
    """Raised when Reddit API operations fail."""
    pass


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


class TranslationError(Exception):
    """Raised when translation operations fail."""
    pass


class FilterError(Exception):
    """Raised when content filtering fails."""
    pass


class SubmissionError(Exception):
    """Raised when post submission fails."""
    pass


class ValidationError(Exception):
    """Raised when validation fails."""
    pass
