"""Model-based reranker service using BGE-reranker-v2-m3 for semantic reranking."""

import logging
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class ModelRerankedResult:
    """Represents a model-reranked search result."""
    chunk_id: int
    content_type: str
    content: str
    metadata: Optional[Dict[str, Any]]
    original_similarity: float
    reranked_score: float
    reranking_reason: str


class ModelRerankerService:
    """Service for reranking RAG search results using BGE-reranker-v2-m3."""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", use_gpu: bool = False):
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.model = None
        self.tokenizer = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._initialized = False
        
    async def initialize(self):
        """Initialize the reranker model asynchronously."""
        if self._initialized:
            return
            
        try:
            logger.info(f"Initializing model-based reranker: {self.model_name}")
            
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, self._load_model)
            
            self._initialized = True
            logger.info("Model-based reranker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize model-based reranker: {e}")
            raise
    
    def _load_model(self):
        """Load the reranker model (runs in thread pool)."""
        try:
            from sentence_transformers import CrossEncoder
            
            # Initialize cross-encoder for reranking
            self.model = CrossEncoder(
                self.model_name,
                max_length=512,  # Adjust based on your content length
                device='cuda' if self.use_gpu else 'cpu'
            )
            
            logger.info(f"Loaded reranker model: {self.model_name}")
            
        except ImportError:
            logger.error("sentence-transformers not available. Install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            raise
    
    async def rerank_results(
        self,
        query: str,
        results: List[Tuple],
        strategy: str = "cross_encoder",
        max_length: int = 512
    ) -> List[ModelRerankedResult]:
        """
        Rerank search results using the specified strategy.
        
        Args:
            query: The original search query
            results: List of tuples from RAG search (chunk_id, content_type, content, metadata, similarity)
            strategy: Reranking strategy ("cross_encoder", "hybrid")
            max_length: Maximum token length for content (truncates if longer)
        
        Returns:
            List of reranked results with scores and reasoning
        """
        if not self._initialized:
            await self.initialize()
        
        if not results:
            return []
        
        # Parse results into structured format
        parsed_results = []
        for result in results:
            if len(result) >= 5:
                chunk_id, content_type, content, metadata, similarity = result[:5]
                parsed_results.append({
                    'chunk_id': chunk_id,
                    'content_type': content_type,
                    'content': content,
                    'metadata': metadata,
                    'similarity': similarity
                })
        
        if strategy == "cross_encoder":
            return await self._cross_encoder_rerank(query, parsed_results, max_length)
        elif strategy == "hybrid":
            return await self._hybrid_rerank(query, parsed_results, max_length)
        else:
            logger.warning(f"Unknown reranking strategy: {strategy}, using cross_encoder")
            return await self._cross_encoder_rerank(query, parsed_results, max_length)
    
    async def _cross_encoder_rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]],
        max_length: int
    ) -> List[ModelRerankedResult]:
        """Rerank using cross-encoder model for semantic relevance."""
        try:
            # Prepare query-document pairs for the model
            pairs = []
            for result in results:
                # Truncate content if too long
                content = result['content'][:max_length * 4]  # Rough character estimate
                pairs.append([query, content])
            
            # Run inference in thread pool
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                self._executor, 
                self._run_cross_encoder_inference, 
                pairs
            )
            
            # Create reranked results
            reranked = []
            for i, result in enumerate(results):
                reranked.append(ModelRerankedResult(
                    chunk_id=result['chunk_id'],
                    content_type=result['content_type'],
                    content=result['content'],
                    metadata=result['metadata'],
                    original_similarity=result['similarity'],
                    reranked_score=scores[i],
                    reranking_reason=f"Cross-encoder score: {scores[i]:.3f}"
                ))
            
            # Sort by reranked score (highest first)
            reranked.sort(key=lambda x: x.reranked_score, reverse=True)
            return reranked
            
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            # Fall back to original similarity scores
            return self._fallback_rerank(results)
    
    async def _hybrid_rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]],
        max_length: int
    ) -> List[ModelRerankedResult]:
        """Hybrid reranking combining cross-encoder with original similarity."""
        try:
            # Get cross-encoder scores
            cross_encoder_results = await self._cross_encoder_rerank(query, results, max_length)
            
            # Combine scores: 70% cross-encoder, 30% original similarity
            for result in cross_encoder_results:
                combined_score = (result.reranked_score * 0.7) + (result.original_similarity * 0.3)
                result.reranked_score = combined_score
                result.reranking_reason = f"Hybrid: cross-encoder({result.reranked_score:.3f}) + similarity({result.original_similarity:.3f})"
            
            # Re-sort by combined scores
            cross_encoder_results.sort(key=lambda x: x.reranked_score, reverse=True)
            return cross_encoder_results
            
        except Exception as e:
            logger.error(f"Hybrid reranking failed: {e}")
            return self._fallback_rerank(results)
    
    def _run_cross_encoder_inference(self, pairs: List[List[str]]) -> List[float]:
        """Run cross-encoder inference (runs in thread pool)."""
        try:
            scores = self.model.predict(pairs)
            # Convert to list if it's a numpy array
            if hasattr(scores, 'tolist'):
                scores = scores.tolist()
            return scores
        except Exception as e:
            logger.error(f"Cross-encoder inference failed: {e}")
            # Return neutral scores on error
            return [0.5] * len(pairs)
    
    def _fallback_rerank(self, results: List[Dict[str, Any]]) -> List[ModelRerankedResult]:
        """Fallback reranking using original similarity scores."""
        reranked = []
        for result in results:
            reranked.append(ModelRerankedResult(
                chunk_id=result['chunk_id'],
                content_type=result['content_type'],
                content=result['content'],
                metadata=result['metadata'],
                original_similarity=result['similarity'],
                reranked_score=result['similarity'],
                reranking_reason="Fallback: original similarity score"
            ))
        
        reranked.sort(key=lambda x: x.reranked_score, reverse=True)
        return reranked
    
    async def close(self):
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        self._initialized = False
        logger.info("Model-based reranker closed")
