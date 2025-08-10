"""CLI argument parser."""

import argparse
from pathlib import Path
from typing import Optional


class CLIArgumentParser:
    """Command-line argument parser for the story generator."""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            description="AI Story Generator - Generate full-length novels with AI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s Prompts/YourChosenPrompt.txt
  %(prog)s ExamplePrompts/Example1/Prompt.txt
            """
        )
        
        # Required arguments
        parser.add_argument(
            "prompt",
            help="Path to file containing the prompt"
        )
        
        return parser
    
    def parse_args(self, args: Optional[list] = None):
        """Parse command line arguments."""
        return self.parser.parse_args(args)
    
    def validate_args(self, args):
        """Validate parsed arguments."""
        # Check if prompt file exists
        prompt_path = Path(args.prompt)
        if not prompt_path.exists():
            raise ValueError(f"Prompt file not found: {args.prompt}") 