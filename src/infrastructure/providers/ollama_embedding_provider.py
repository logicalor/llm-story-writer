"""Ollama embedding provider implementation."""

import asyncio
import json
import logging
from typing import List, Optional
import aiohttp
from domain.exceptions import ModelProviderError

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider:
    """Ollama embedding provider for generating text embeddings."""
    
    def __init__(self, host: str = "127.0.0.1:11434", model: str = "nomic-embed-text"):
        self.host = host
        self.model = model
        self.base_url = f"http://{host}"
        
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
            
        embeddings = []
        for text in texts:
            try:
                embedding = await self._get_single_embedding(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to generate embedding for text: {e}")
                # Return zero vector as fallback
                embeddings.append([0.0] * 1536)
                
        return embeddings
    
    async def get_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return (await self.get_embeddings([text]))[0]
    
    async def _get_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using Ollama API."""
        url = f"{self.base_url}/api/embeddings"
        
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ModelProviderError(
                        f"Ollama embedding API error: {response.status} - {error_text}"
                    )
                
                result = await response.json()
                embedding = result.get("embedding")
                
                if not embedding:
                    raise ModelProviderError("No embedding returned from Ollama API")
                
                return embedding
    
    async def test_connection(self) -> bool:
        """Test if the Ollama server is accessible."""
        try:
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def get_model_info(self) -> Optional[dict]:
        """Get information about the embedding model."""
        try:
            url = f"{self.base_url}/api/show"
            payload = {"name": self.model}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None
