#!/usr/bin/env python3
"""
AI Story Writer - Main Entry Point

A clean, modern AI story generation application built with clean architecture.
Generate full-length novels with AI using multiple model providers.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from presentation.cli.main import main as cli_main


def main():
    """Main entry point for the AI Story Writer application."""
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main() 