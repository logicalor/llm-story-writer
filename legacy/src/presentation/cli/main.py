"""Main CLI entry point."""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

from config.config_loader import ConfigLoader
from domain.exceptions import StoryGenerationError, ConfigurationError
from infrastructure.container import Container
from infrastructure.logging.structured_logger import LogLevel
from .argument_parser import CLIArgumentParser


class CLIApplication:
    """Main CLI application class."""
    
    def __init__(self):
        self.arg_parser = CLIArgumentParser()
        self.config_loader = ConfigLoader()
        self.container: Optional[Container] = None
        self.logger = None
    
    async def run(self, args: Optional[list] = None):
        """Run the CLI application."""
        try:
            # Parse arguments
            parsed_args = self.arg_parser.parse_args(args)
            self.arg_parser.validate_args(parsed_args)
            
            # Load prompt
            prompt = self._load_prompt(parsed_args.prompt)
            
            # Load configuration from config.md
            config = self.config_loader.load_config()
            
            # Initialize container
            self.container = Container.create_from_config(config)
            self.logger = self.container.logger()
            
            # Log startup
            self.logger.info("Starting AI Story Writer", version="2.0.0")
            
            # Generate story
            await self._generate_story(prompt, parsed_args)
            
        except KeyboardInterrupt:
            if self.logger:
                self.logger.warning("Generation interrupted by user")
            sys.exit(1)
        except Exception as e:
            if self.logger:
                self.logger.error("Application error", error=str(e))
            else:
                print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    def _load_prompt(self, prompt_path: str) -> str:
        """Load prompt from file."""
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            raise ConfigurationError(f"Failed to load prompt file: {e}") from e
    
    async def _generate_story(self, prompt: str, args):
        """Generate the story."""
        start_time = time.time()
        
        # Get services from container
        story_service = self.container.story_generation_service()
        generation_settings = self.config_loader.get_generation_settings()
        
        # Extract prompt filename for savepoints
        prompt_filename = Path(args.prompt).name
        
        # Log generation start
        self.logger.log_generation_start(
            prompt_hash=str(hash(prompt)),
            settings=generation_settings.to_dict()
        )
        
        # Generate story
        self.logger.info("Starting story generation")
        story = await story_service.generate_story(
            prompt=prompt,
            settings=generation_settings,
            prompt_filename=prompt_filename
        )
        
        # Save story
        self.logger.info("Saving story")
        output_path = await story_service.save_story(
            story=story,
            output_path=None
        )
        
        # Calculate statistics
        end_time = time.time()
        duration = end_time - start_time
        
        # Log completion
        self.logger.info("Story generation completed", 
                        duration=duration,
                        output_path=str(output_path))
        
        print(f"\n✅ Story generated successfully!")
        print(f"📁 Output saved to: {output_path}")
        print(f"⏱️  Total time: {duration:.2f} seconds")


def main():
    """Main CLI entry point."""
    app = CLIApplication()
    asyncio.run(app.run())


if __name__ == "__main__":
    main() 