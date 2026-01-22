"""Main bot entry point - executes the crosspost pipeline."""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from pipeline import BotPipeline


def main():
    """Execute the bot pipeline."""
    pipeline = BotPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
