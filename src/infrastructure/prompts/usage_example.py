"""Practical example of integrating PromptHandler with existing strategy."""

import asyncio
from typing import Dict, Any, Optional
from domain.value_objects.model_config import ModelConfig
from domain.value_objects.generation_settings import GenerationSettings
from .prompt_handler import PromptHandler
from .prompt_wrapper import execute_prompt_with_savepoint
from application.interfaces.model_provider import ModelProvider
from domain.repositories.savepoint_repository import SavepointRepository
from infrastructure.prompts.prompt_loader import PromptLoader


class EnhancedOutlineChapterStrategy:
    """Example of how to enhance the existing strategy with the new prompt handler."""
    
    def __init__(
        self,
        model_provider: ModelProvider,
        prompt_loader: PromptLoader,
        savepoint_repo: Optional[SavepointRepository] = None
    ):
        self.model_provider = model_provider
        self.prompt_loader = prompt_loader
        self.savepoint_repo = savepoint_repo
        
        # Create the prompt handler
        self.prompt_handler = PromptHandler(
            model_provider=model_provider,
            prompt_loader=prompt_loader,
            savepoint_repo=savepoint_repo
        )
    
    async def extract_story_start_date(self, prompt: str, settings: GenerationSettings) -> str:
        """Extract story start date using the new prompt handler."""
        model_config = ModelConfig.from_string(settings.model)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="extract_story_start_date",
            variables={"prompt": prompt},
            savepoint_id="extract_story_start_date",
            model_config=model_config,
            seed=settings.seed,
            system_message="You are an expert at analyzing story prompts and extracting temporal information."
        )
        
        return response.content
    
    async def extract_base_context(self, prompt: str, settings: GenerationSettings) -> str:
        """Extract base context using the new prompt handler."""
        model_config = ModelConfig.from_string(settings.model)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="extract_base_context",
            variables={"prompt": prompt},
            savepoint_id="extract_base_context",
            model_config=model_config,
            seed=settings.seed,
            system_message="You are an expert at analyzing story prompts and extracting contextual information."
        )
        
        return response.content
    
    async def generate_story_elements(self, prompt: str, settings: GenerationSettings) -> str:
        """Generate story elements using the new prompt handler."""
        model_config = ModelConfig.from_string(settings.model)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_story_elements",
            variables={"prompt": prompt},
            savepoint_id="generate_story_elements",
            model_config=model_config,
            seed=settings.seed,
            system_message="You are an expert creative writer specializing in character and plot development."
        )
        
        return response.content
    
    async def generate_initial_outline(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        settings: GenerationSettings
    ) -> str:
        """Generate initial outline using the new prompt handler."""
        model_config = ModelConfig.from_string(settings.model)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_initial_outline",
            variables={
                "prompt": prompt,
                "story_elements": story_elements,
                "base_context": base_context
            },
            savepoint_id="generate_initial_outline",
            model_config=model_config,
            seed=settings.seed,
            system_message="You are an expert story outline writer with deep knowledge of plot structure."
        )
        
        return response.content
    
    async def generate_chapter_outline(
        self,
        chapter_num: int,
        outline: str,
        base_context: str,
        recap: str,
        settings: GenerationSettings
    ) -> str:
        """Generate chapter outline using the new prompt handler."""
        model_config = ModelConfig.from_string(settings.model)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline",
            variables={
                "chapter_num": chapter_num,
                "outline": outline,
                "base_context": base_context,
                "recap": recap
            },
            savepoint_id=f"chapter_outline_{chapter_num}",
            model_config=model_config,
            seed=settings.seed,
            system_message="You are an expert at creating detailed chapter outlines that advance the story."
        )
        
        return response.content
    
    async def generate_chapter_content(
        self,
        chapter_num: int,
        chapter_outline: str,
        previous_recap: str,
        settings: GenerationSettings
    ) -> str:
        """Generate chapter content using the new prompt handler."""
        model_config = ModelConfig.from_string(settings.model)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_chapter_content",
            variables={
                "chapter_num": chapter_num,
                "chapter_outline": chapter_outline,
                "previous_recap": previous_recap
            },
            savepoint_id=f"chapter_content_{chapter_num}",
            model_config=model_config,
            seed=settings.seed,
            system_message="You are an expert creative writer who creates engaging, well-paced chapter content."
        )
        
        return response.content
    
    def set_story_directory(self, story_name: str) -> None:
        """Set the story directory for savepoints."""
        self.prompt_handler.set_story_directory(story_name)
    
    async def check_savepoint_exists(self, savepoint_id: str) -> bool:
        """Check if a savepoint exists."""
        return await self.prompt_handler.check_savepoint_exists(savepoint_id)
    
    async def list_savepoints(self) -> Dict[str, Any]:
        """List all savepoints."""
        return await self.prompt_handler.list_savepoints()
    
    async def clear_savepoints(self) -> None:
        """Clear all savepoints."""
        await self.prompt_handler.clear_all_savepoints()


# Example of how to use the enhanced strategy
async def example_usage():
    """Example of using the enhanced strategy."""
    
    # Setup (these would come from your DI container)
    model_provider: ModelProvider = None
    prompt_loader = PromptLoader("src/application/strategies/prompts/outline-chapter")
    savepoint_repo: SavepointRepository = None
    
    # Create the enhanced strategy
    strategy = EnhancedOutlineChapterStrategy(
        model_provider=model_provider,
        prompt_loader=prompt_loader,
        savepoint_repo=savepoint_repo
    )
    
    # Set story directory
    strategy.set_story_directory("my_fantasy_novel")
    
    # Create generation settings
    settings = GenerationSettings(
        model="ollama://llama3:70b",
        temperature=0.7,
        max_tokens=2000,
        seed=42
    )
    
    # Example story prompt
    prompt = """
    A young wizard named Alex discovers they have the power to communicate with ancient spirits.
    When their village is threatened by a dark force, Alex must learn to harness their abilities
    and work with the spirits to save their home. The story is set in a medieval fantasy world
    where magic is rare and often feared.
    """
    
    # Generate story components
    start_date = await strategy.extract_story_start_date(prompt, settings)
    print(f"Story start date: {start_date}")
    
    base_context = await strategy.extract_base_context(prompt, settings)
    print(f"Base context: {base_context}")
    
    story_elements = await strategy.generate_story_elements(prompt, settings)
    print(f"Story elements: {story_elements}")
    
    outline = await strategy.generate_initial_outline(prompt, story_elements, base_context, settings)
    print(f"Outline: {outline}")
    
    # Check what savepoints we have
    savepoints = await strategy.list_savepoints()
    print(f"Available savepoints: {list(savepoints.keys())}")


if __name__ == "__main__":
    # Note: This requires actual dependencies to run
    # asyncio.run(example_usage())
    print("Example provided for reference. Uncomment and provide actual dependencies to run.") 