"""Configuration loader for reading from config.md frontmatter."""

import re
import yaml
from pathlib import Path
from typing import Dict, Any
from .settings import AppConfig
from domain.exceptions import ConfigurationError
from domain.value_objects.generation_settings import GenerationSettings


class ConfigLoader:
    """Loads configuration from config.md frontmatter."""
    
    def __init__(self, config_file: str = "config.md"):
        self.config_file = Path(config_file)
    
    def load_config(self) -> AppConfig:
        """Load configuration from config.md frontmatter."""
        if not self.config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_file}")
        
        try:
            content = self.config_file.read_text(encoding='utf-8')
            frontmatter = self._extract_frontmatter(content)
            config_data = yaml.safe_load(frontmatter)
            
            # Merge translation settings into generation settings
            if 'translation' in config_data:
                translation = config_data['translation']
                config_data['generation'].update({
                    'translate_language': translation.get('translate_language'),
                    'translate_prompt_language': translation.get('translate_prompt_language')
                })
                del config_data['translation']
            
            # Merge infrastructure settings
            if 'infrastructure' in config_data:
                infrastructure = config_data['infrastructure']
                config_data.update({
                    'output_dir': infrastructure.get('output_dir', 'Stories'),
                    'savepoint_dir': infrastructure.get('savepoint_dir', 'SavePoints'),
                    'logs_dir': infrastructure.get('logs_dir', 'Logs'),
                    'ollama_host': infrastructure.get('ollama_host', '127.0.0.1:11434'),
                    'ollama_context_length': infrastructure.get('ollama_context_length', 16384),
                })
                del config_data['infrastructure']
            
            # Merge API keys
            if 'api_keys' in config_data:
                api_keys = config_data['api_keys']
                config_data.update({
                    'google_api_key': api_keys.get('google_api_key'),
                    'openrouter_api_key': api_keys.get('openrouter_api_key'),
                })
                del config_data['api_keys']
            
            return AppConfig.from_dict(config_data)
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {self.config_file}: {e}") from e
    
    def _extract_frontmatter(self, content: str) -> str:
        """Extract YAML frontmatter from markdown content."""
        # Match YAML frontmatter between --- markers
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            raise ConfigurationError("No YAML frontmatter found in config.md")
        
        return match.group(1)
    
    def get_generation_settings(self) -> GenerationSettings:
        """Get generation settings from config."""
        config = self.load_config()
        return config.generation 