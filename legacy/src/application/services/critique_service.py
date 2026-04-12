"""Critique service for iterative outline refinement."""

import json
from typing import List, Optional
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import StoryGenerationError

from ..interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_loader import PromptLoader
from infrastructure.savepoints import SavepointManager
from .critique_parser import CritiqueParser, CritiqueResult


class CritiqueService:
    """Service for handling outline critiques and iterative refinement."""
    
    def __init__(self, model_provider: ModelProvider, config: Dict[str, Any], prompt_loader: PromptLoader):
        self.model_provider = model_provider
        self.config = config
        self.prompt_loader = prompt_loader
        # Create a separate prompt loader for critique prompts
        self.critique_prompt_loader = PromptLoader("src/application/strategies/prompts")
        self.critique_parser = CritiqueParser()
        
        # Define the critic types in order of evaluation
        self.critic_types = [
            "audiobook-producer",
            "book-club-moderator", 
            "commercial-fiction-editor",
            "literary-fiction-reviewer",
            "publishing-acquisitions-editor",
            "subject-expert"
        ]
    
    async def refine_outline_iteratively(
        self,
        initial_outline: str,
        story_elements: str,
        base_context: str,
        prompt: str,
        settings: GenerationSettings,
        max_iterations: int = 5,
        savepoint_manager: Optional[SavepointManager] = None
    ) -> str:
        """Refine the outline iteratively based on critic feedback."""
        current_outline = initial_outline
        iteration = 0
        
        print(f"\n[CRITIQUE] Starting iterative outline refinement...")
        print(f"[CRITIQUE] Maximum iterations: {max_iterations}")
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n[CRITIQUE] Iteration {iteration}/{max_iterations}")
            
            # Save current outline at this iteration
            if savepoint_manager:
                await savepoint_manager.save_step(f"outline_iteration_{iteration}", current_outline)
            
            # Get critiques from all critics
            critique_results = await self._get_all_critiques(current_outline, settings)
            
            # Save critique results for this iteration
            if savepoint_manager:
                critique_data = {
                    "iteration": iteration,
                                   "critic_scores": {result.critic_type: result.overall_score for result in critique_results},
               "average_scores": self.critique_parser.get_average_scores(critique_results),
               "overall_average": self.critique_parser.get_overall_average_score(critique_results)
                }
                await savepoint_manager.save_step(f"critique_results_iteration_{iteration}", critique_data)
            
            # Check if refinement is needed
            should_refine, average_scores, overall_average = self.critique_parser.should_refine_outline(critique_results)
            
            # Print current scores
            print(f"[CRITIQUE] Overall average score: {overall_average:.1f}%")
            print(f"[CRITIQUE] Criterion averages:")
            for criterion, score in average_scores.items():
                print(f"  - {criterion}: {score:.1f}%")
            
            if not should_refine:
                print(f"[CRITIQUE] Outline meets quality standards! Stopping refinement.")
                break
            
            print(f"[CRITIQUE] Refinement needed. Generating improved outline...")
            
            # Generate refined outline based on feedback
            refined_outline = await self._generate_refined_outline(
                current_outline, story_elements, base_context, prompt, 
                critique_results, settings
            )
            
            current_outline = refined_outline
        
        if iteration >= max_iterations:
            print(f"[CRITIQUE] Maximum iterations reached. Using final outline.")
        
        return current_outline
    
    async def _get_all_critiques(self, outline: str, settings: GenerationSettings) -> List[CritiqueResult]:
        """Get critiques from all critic types."""
        critique_results = []
        
        for critic_type in self.critic_types:
            print(f"[CRITIQUE] Getting critique from {critic_type.replace('-', ' ')}...")
            
            try:
                critique_response = await self._get_critique(critic_type, outline, settings)
                critique_result = self.critique_parser.parse_critique(critic_type, critique_response)
                critique_results.append(critique_result)
                
                print(f"[CRITIQUE] {critic_type.replace('-', ' ').title()} score: {critique_result.overall_score:.1f}/100")
                
            except Exception as e:
                print(f"[CRITIQUE] Warning: Failed to get critique from {critic_type}: {e}")
                # Continue with other critics even if one fails
        
        return critique_results
    
    async def _get_critique(self, critic_type: str, outline: str, settings: GenerationSettings) -> str:
        """Get a critique from a specific critic type."""
        prompt_content = self.critique_prompt_loader.load_prompt(
            f"outline_review/{critic_type}",
            variables={"outline": outline}
        )
        
        messages = [
            {"role": "user", "content": "You are an expert critic providing detailed, constructive feedback on story outlines. Always follow the exact format specified in the prompt.\n\n" + prompt_content}
        ]
        
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _generate_refined_outline(
        self,
        current_outline: str,
        story_elements: str,
        base_context: str,
        prompt: str,
        critique_results: List[CritiqueResult],
        settings: GenerationSettings
    ) -> str:
        """Generate a refined outline based on critique feedback."""
        
        # Format the critique feedback
        feedback = self.critique_parser.format_critique_feedback(critique_results)
        
        # Calculate current scores for context
        should_refine, average_scores, overall_average = self.critique_parser.should_refine_outline(critique_results)
        
        # Create the refinement prompt
        refinement_prompt = f"""You are an expert story outline writer. Your task is to refine the current outline based on detailed feedback from multiple professional critics.

## Original Story Prompt
{prompt}

## Story Elements
{story_elements}

## Base Context
{base_context}

## Current Outline
{current_outline}

## Critique Feedback
{feedback}

## Current Performance
Overall Score: {overall_average:.1f}%
Criterion Scores:
"""
        
        for criterion, score in average_scores.items():
            refinement_prompt += f"- {criterion}: {score:.1f}%\n"
        
        refinement_prompt += f"""
## Refinement Instructions
Based on the critique feedback above, refine the outline to address the identified issues. Focus on:

1. **Low-scoring areas**: Pay special attention to criteria scoring below 75%
2. **Specific feedback**: Address the concrete suggestions and concerns raised by each critic
3. **Maintain strengths**: Preserve elements that received positive feedback
4. **Improve structure**: Ensure the outline flows better and addresses pacing issues
5. **Enhance details**: Add more vivid, engaging details where needed
6. **Strengthen themes**: Develop character arcs and thematic elements more clearly

## Requirements
- Keep the same overall story structure and plot points
- Address the specific issues mentioned in the critiques
- Maintain the story's core elements and themes
- Improve clarity, pacing, and engagement
- Ensure the outline is comprehensive and detailed

Please provide a refined version of the outline that addresses the critique feedback. 

It is extremely important that you maintain the story's integrity. Don't just refer back to events or story elements as if the reader is already aware of them."""

        messages = [
            {"role": "user", "content": "You are an expert story outline writer specializing in iterative refinement based on professional feedback. Focus on addressing specific critique points while maintaining story integrity.\n\n" + refinement_prompt}
        ]
        
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed + 1000,  # Use different seed for refinement
            min_word_count=500,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip() 