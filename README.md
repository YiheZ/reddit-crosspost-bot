# Reddit Crosspost Bot

A modular Python bot that automatically crossposts content from multiple source subreddits to a target subreddit, with translation and intelligent filtering.

## Features

- 🔄 Automatic crossposting from multiple source subreddits
- 🌐 Translation support (Gemini AI / DeepL)
- 🎯 Smart content filtering and duplicate detection
- 🏷️ Automatic flair assignment
- 💾 Persistent state management via GitHub Gist
- 🔧 Highly configurable via YAML

## Project Structure

```
reddit-crosspost-bot/
├── bot.py                    # Main entry point
├── constants.yaml            # Configuration file
├── requirements.txt          # Python dependencies
├── README.md                 # Documentation
├── .gitignore                # Git exclusions
│
└── src/                      # Application source code
    │
    ├── core/                 # Core functionality (175 lines, 3 files)
    │   ├── __init__.py
    │   ├── constants.py      # Constants loader from YAML
    │   └── exceptions.py     # Custom exceptions
    │
    ├── pipeline/             # Pipeline orchestration (307 lines, 5 files)
    │   ├── __init__.py
    │   ├── runner.py         # Main pipeline orchestrator
    │   ├── initializer.py    # Initialization step
    │   ├── fetcher.py        # Post fetching step
    │   └── translator.py     # Translation step
    │
    ├── config/               # Configuration management (85 lines)
    │   └── __init__.py       # BotConfig class
    │
    ├── reddit_client/        # Reddit API client (240 lines, 4 files)
    │   ├── __init__.py
    │   ├── client.py         # Main client wrapper
    │   ├── fetcher.py        # Fetching posts & metadata
    │   └── submitter.py      # Submitting & crossposting
    │
    ├── content/              # Content & utilities (320 lines, 6 files)
    │   ├── __init__.py       # Module exports
    │   ├── filter.py         # ContentFilter class
    │   ├── url_utils.py      # URL normalization & deduplication
    │   ├── time_utils.py     # Timestamp utilities
    │   ├── text_utils.py     # String manipulation
    │   └── dict_utils.py     # Dictionary helpers
    │
    ├── storage/              # State persistence (71 lines)
    │   └── __init__.py       # GitHub Gist storage
    │
    ├── translation/          # Translation services (263 lines, 3 files)
    │   ├── __init__.py
    │   ├── gemini.py         # Gemini AI translation
    │   └── deepl.py          # DeepL translation
    │
    ├── processors/           # Post processing (210 lines, 3 files)
    │   ├── __init__.py
    │   ├── builder.py        # Candidate building
    │   └── submission.py     # Submission handling
    │
    └── models/               # Data models (88 lines)
        └── __init__.py       # Dataclasses for posts, results
```
odularized content**: Split into 6 focused files (filter, url_utils, time_utils, text_utils, dict_utils)
- **Merged utilities**: `utils` module merged into `content` for better cohesion
- **Split responsibilities**: `reddit_client` split into `fetcher` and `submitter`
- **Proper grouping**: `processors` organized with `builder` and `submission`
- **Balanced sizing**: Each module has clear, focused responsibility
- **Moved to src/**: All application code now in `src/` directory (Python best practice)
- **Merged utilities**: `utils` module merged into `content` for better cohesion
- **Split responsibilities**: `reddit_client` split into `fetcher` and `submitter`
- **Proper grouping**: `processors` organized with `builder` and `submission`
- **Balanced sizing**: No single-responsibility modules; each has meaningful scope

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd reddit-crosspost-bot
```

2. **Create and activate virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file or set environment variables:
```bash
# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=your_user_agent
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password

# GitHub Gist (for state storage)
GITHUB_TOKEN=your_github_token
GIST_ID=your_gist_id

# Translation API (choose one or both)
GEMINI_API_KEY=your_gemini_key
DEEPL_API_KEY=your_deepl_key
```

5. **Configure bot settings**
Edit `constants.yaml` to customize timing, limits, and behavior.

## Configuration

### constants.yaml

The main configuration file controls all bot behavior:

```yaml
# Time settings
time:
  posted_id_retention_days: 7    # How long to remember posted IDs
  recent_post_hours: 24          # Window for duplicate detection

# Post fetching
post_fetching:
  max_candidates: 500            # Maximum posts to consider
  top_limit: 100                 # Limit for "popular" mode
  limit_posts: 1                 # Default posts per subreddit

# Submission settings
submission:
  min_post_delay: 2              # Minimum delay between posts (seconds)
  max_post_delay: 5              # Maximum delay between posts (seconds)
  max_retries: 3                 # Retry attempts for failed submissions

# Translation settings
translation:
  target_lang: "ZH"              # Target language code
  gemini_model_name: "gemini-2.5-flash"
```

## Usage

### Run the bot

```bash
source .venv/bin/activate
python bot.py
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

```

### Import as a module

```python
from pipeline import BotPipeline
from core import constants, BotConfigError

# Run the pipeline
pipeline = BotPipeline()
pipeline.run()
```

## Module Details

### Core Module (`core/`)
- **constants.py**: Loads configuration from YAML, provides Constants class
- **exceptions.py**: Custom exception classes for error handling

### Pipeline Module (`pipeline/`)
Modular pipeline with separate responsibilities:
- **runner.py**: Orchestrates the complete workflow
- **initializer.py**: Loads state, flairs, and recent posts
- **fetcher.py**: Fetches and filters posts from source subreddits
- **translator.py**: Prepares candidates and handles translation

### Translation Module (`translation/`)
- **gemini.py**: Gemini AI translation with content filtering
- **deepl.py**: DeepL translation with bracket pair fixing

### Processors Module (`processors/`)
- **submission.py**: Handles post submission with retry logic

## Development

### Running Tests
```bash
# Test imports
python -c "from core import constants; print('Constants:', constants.MIN_POST_DELAY)"
python -c "from pipeline import BotPipeline; print('Pipeline OK')"
```

### Adding New Features

1. **New translation service**: Add to `translation/` directory
2. **New content filter**: Extend `content/` module
3. **New storage backend**: Implement in `storage/` module
4. **New pipeline step**: Add to `pipeline/` directory

### Code Style
- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep modules focused and single-purpose

## Architecture

The bot follows a modular, pipeline-based architecture:

1. **Initialize**: Load state, flairs, recent posts
2. **Fetch**: Get posts from source subreddits
3. **Filter**: Apply keyword and duplicate filtering
4. **Translate**: Send to translation service
5. **Submit**: Post to target subreddit
6. **Save**: Persist state to storage

Each step is isolated and can be tested/modified independently.

## Troubleshooting

### Import Errors
Ensure virtual environment is activated:
```bash
source .venv/bin/activate
```

### Configuration Errors
Check that `constants.yaml` exists and is valid YAML.

### API Errors
Verify environment variables are set correctly.
