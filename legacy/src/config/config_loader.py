"""Configuration loader for reading from config.md frontmatter."""

import re
import yaml
from pathlib import Path
from typing import Dict, Any
from domain.exceptions import ConfigurationError


class ConfigLoader:
    """Loads configuration from config.md frontmatter."""
    
    def __init__(self, config_file: str = "config.md"):
        self.config_file = Path(config_file)
    
    def load_config(self) -> Dict[str, Any]:
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
            
            # Merge infrastructure settings with defaults
            if 'infrastructure' in config_data:
                infrastructure = config_data['infrastructure']
                config_data.update({
                    'output_dir': infrastructure.get('output_dir', 'Stories'),
                    'savepoint_dir': infrastructure.get('savepoint_dir', 'SavePoints'),
                    'logs_dir': infrastructure.get('logs_dir', 'Logs'),
                    'ollama_host': infrastructure.get('ollama_host', '127.0.0.1:11434'),
                    'lm_studio_host': infrastructure.get('lm_studio_host', '127.0.0.1:1234'),
                    'llama_cpp_host': infrastructure.get('llama_cpp_host', '127.0.0.1:8080'),
                    'context_length': infrastructure.get('context_length', 4096),
                    'randomize_seed': infrastructure.get('randomize_seed', True),
                    # RAG Configuration
                    'postgres_host': infrastructure.get('postgres_host', 'localhost:5432'),
                    'postgres_database': infrastructure.get('postgres_database', 'story_writer'),
                    'postgres_user': infrastructure.get('postgres_user', 'story_user'),
                    'postgres_password': infrastructure.get('postgres_password', 'story_pass'),
                    'embedding_model': infrastructure.get('embedding_model', 'ollama://nomic-embed-text'),
                    'vector_dimensions': infrastructure.get('vector_dimensions', 1536),
                    'similarity_threshold': infrastructure.get('similarity_threshold', 0.7),
                    'max_context_chunks': infrastructure.get('max_context_chunks', 20),
                    'max_chunk_size': infrastructure.get('max_chunk_size', 1000),
                    'overlap_size': infrastructure.get('overlap_size', 200),
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
            
            return config_data
            
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
    
    def get_generation_settings(self) -> "GenerationSettings":
        """Get generation settings from config."""
        from domain.value_objects.generation_settings import GenerationSettings
        config = self.load_config()
        generation_data = config.get('generation', {})
        return GenerationSettings.from_dict(generation_data) 