"""Constants loaded from YAML configuration file."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


class Constants:
    """Container for bot constants loaded from YAML."""

    def __init__(self, config_path: str = None):
        """Initialize constants from YAML file.
        
        Args:
            config_path: Path to constants.yaml file. If None, uses default location.
        """
        if config_path is None:
            # Go up to project root (src -> project root)
            config_path = Path(__file__).parent.parent.parent / "constants.yaml"
        else:
            config_path = Path(config_path)

        try:
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")

        self._load_constants()

    def _load_constants(self):
        """Load all constants from config dictionary."""
        # Time constants (in seconds)
        self.POSTED_ID_RETENTION_DAYS = self._config['time']['posted_id_retention_days']
        self.POSTED_ID_RETENTION_SECONDS = self.POSTED_ID_RETENTION_DAYS * 24 * 3600
        self.RECENT_POST_HOURS = self._config['time']['recent_post_hours']
        self.ONE_DAY_SECONDS = 24 * 3600

        # Post fetching
        self.DEFAULT_MAX_CANDIDATES = self._config['post_fetching']['max_candidates']
        self.DEFAULT_TOP_LIMIT = self._config['post_fetching']['top_limit']
        self.DEFAULT_LIMIT_POSTS = self._config['post_fetching']['limit_posts']
        self.MAX_FLAIR_SEARCH_RESULTS = self._config['post_fetching']['max_flair_search_results']

        # Submission delays
        self.MIN_POST_DELAY = self._config['submission']['min_post_delay']
        self.MAX_POST_DELAY = self._config['submission']['max_post_delay']

        # Retry settings
        self.DEFAULT_MAX_RETRIES = self._config['submission']['max_retries']

        # Translation
        self.DEFAULT_TARGET_LANG = self._config['translation']['target_lang']
        self.GEMINI_MODEL_NAME = self._config['translation']['gemini_model_name']

        # URLs
        self.GIST_API_BASE = self._config['api']['gist_base']
        self.GIST_FILE_NAME = self._config['api']['gist_file_name']
        self.DEEPL_API_URL = self._config['api']['deepl_url']

        # URL fetching
        self.DEFAULT_FETCH_TIMEOUT = self._config['url_fetching']['timeout']
        self.DEFAULT_FETCH_MAX_CHARS = self._config['url_fetching']['max_chars']

        # Internal domains (Reddit-owned)
        self.INTERNAL_DOMAINS = self._config['internal_domains']

        # Fetch modes
        self.FETCH_MODE_LATEST = self._config['fetch_modes']['latest']
        self.FETCH_MODE_POPULAR = self._config['fetch_modes']['popular']

        # Logging
        self.LOG_SEPARATOR = self._config['logging']['separator']

    def get(self, key: str, default: Any = None) -> Any:
        """Get a constant value by name.
        
        Args:
            key: Name of the constant (without self.)
            default: Default value if constant doesn't exist
            
        Returns:
            Value of the constant or default
        """
        return getattr(self, key, default)


# Global constants instance
constants = Constants()


# For backward compatibility, expose constants as module-level variables
POSTED_ID_RETENTION_DAYS = constants.POSTED_ID_RETENTION_DAYS
POSTED_ID_RETENTION_SECONDS = constants.POSTED_ID_RETENTION_SECONDS
RECENT_POST_HOURS = constants.RECENT_POST_HOURS
ONE_DAY_SECONDS = constants.ONE_DAY_SECONDS
DEFAULT_MAX_CANDIDATES = constants.DEFAULT_MAX_CANDIDATES
DEFAULT_TOP_LIMIT = constants.DEFAULT_TOP_LIMIT
DEFAULT_LIMIT_POSTS = constants.DEFAULT_LIMIT_POSTS
MIN_POST_DELAY = constants.MIN_POST_DELAY
MAX_POST_DELAY = constants.MAX_POST_DELAY
DEFAULT_MAX_RETRIES = constants.DEFAULT_MAX_RETRIES
DEFAULT_TARGET_LANG = constants.DEFAULT_TARGET_LANG
GEMINI_MODEL_NAME = constants.GEMINI_MODEL_NAME
GIST_API_BASE = constants.GIST_API_BASE
GIST_FILE_NAME = constants.GIST_FILE_NAME
DEEPL_API_URL = constants.DEEPL_API_URL
DEFAULT_FETCH_TIMEOUT = constants.DEFAULT_FETCH_TIMEOUT
DEFAULT_FETCH_MAX_CHARS = constants.DEFAULT_FETCH_MAX_CHARS
INTERNAL_DOMAINS = constants.INTERNAL_DOMAINS
FETCH_MODE_LATEST = constants.FETCH_MODE_LATEST
FETCH_MODE_POPULAR = constants.FETCH_MODE_POPULAR
MAX_FLAIR_SEARCH_RESULTS = constants.MAX_FLAIR_SEARCH_RESULTS
LOG_SEPARATOR = constants.LOG_SEPARATOR
