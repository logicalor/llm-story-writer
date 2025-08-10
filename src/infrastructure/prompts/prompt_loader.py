"""Prompt loader for reading prompts from markdown files."""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from domain.exceptions import ConfigurationError


class PromptLoader:
    """Loads and manages prompts from markdown files."""
    
    def __init__(self, prompts_dir: str = "src/prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._prompt_cache: Dict[str, str] = {}
    
    def load_prompt(self, prompt_name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Load a prompt from a markdown file and substitute variables."""
        if prompt_name not in self._prompt_cache:
            prompt_file = self.prompts_dir / f"{prompt_name}.md"
            if not prompt_file.exists():
                raise ConfigurationError(f"Prompt file not found: {prompt_file}")
            
            self._prompt_cache[prompt_name] = prompt_file.read_text(encoding='utf-8').strip()
        
        prompt_content = self._prompt_cache[prompt_name]
        
        if variables:
            prompt_content = self._substitute_variables(prompt_content, variables)
        
        return prompt_content
    
    def _substitute_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in prompt content."""
        # Handle different variable formats: {{variable}}, {variable}, etc.
        for key, value in variables.items():
            # Replace {{variable}} format
            content = content.replace(f"{{{{{key}}}}}", str(value))
            # Replace {variable} format
            content = content.replace(f"{{{key}}}", str(value))
        
        return content
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self._prompt_cache.clear() 