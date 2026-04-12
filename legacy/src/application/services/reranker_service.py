"""Reranker service for improving RAG search result quality."""

import logging
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class RerankedResult:
    """Represents a reranked search result."""
    chunk_id: int
    content_type: str
    content: str
    metadata: Optional[Dict[str, Any]]
    original_similarity: float
    reranked_score: float
    reranking_reason: str


class RerankerService:
    """Service for reranking RAG search results to improve relevance."""
    
    def __init__(self, use_keyword_boost: bool = True, use_metadata_boost: bool = True):
        self.use_keyword_boost = use_keyword_boost
        self.use_metadata_boost = use_metadata_boost
    
    async def rerank_results(
        self,
        query: str,
        results: List[Tuple],
        strategy: str = "hybrid"
    ) -> List[RerankedResult]:
        """
        Rerank search results using the specified strategy.
        
        Args:
            query: The original search query
            results: List of tuples from RAG search (chunk_id, content_type, content, metadata, similarity)
            strategy: Reranking strategy ("hybrid", "keyword", "metadata", "semantic")
        
        Returns:
            List of reranked results with scores and reasoning
        """
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
        
        if strategy == "hybrid":
            return await self._hybrid_rerank(query, parsed_results)
        elif strategy == "keyword":
            return await self._keyword_rerank(query, parsed_results)
        elif strategy == "metadata":
            return await self._metadata_rerank(query, parsed_results)
        elif strategy == "semantic":
            return await self._semantic_rerank(query, parsed_results)
        else:
            logger.warning(f"Unknown reranking strategy: {strategy}, using hybrid")
            return await self._hybrid_rerank(query, parsed_results)
    
    async def _hybrid_rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]]
    ) -> List[RerankedResult]:
        """Hybrid reranking combining multiple strategies."""
        reranked = []
        
        for result in results:
            score = result['similarity']  # Start with original similarity
            
            # Apply keyword boost
            if self.use_keyword_boost:
                keyword_score = self._calculate_keyword_score(query, result['content'])
                score += keyword_score * 0.3  # 30% weight for keywords
            
            # Apply metadata boost
            if self.use_metadata_boost and result['metadata']:
                metadata_score = self._calculate_metadata_score(query, result['metadata'])
                score += metadata_score * 0.2  # 20% weight for metadata
            
            # Apply content type boost
            content_type_score = self._calculate_content_type_score(query, result['content_type'])
            score += content_type_score * 0.1  # 10% weight for content type
            
            # Normalize score to 0-1 range
            score = max(0.0, min(1.0, score))
            
            reranked.append(RerankedResult(
                chunk_id=result['chunk_id'],
                content_type=result['content_type'],
                content=result['content'],
                metadata=result['metadata'],
                original_similarity=result['similarity'],
                reranked_score=score,
                reranking_reason=self._generate_reranking_reason(
                    result['similarity'], keyword_score if self.use_keyword_boost else 0,
                    metadata_score if self.use_metadata_boost else 0, content_type_score
                )
            ))
        
        # Sort by reranked score (highest first)
        reranked.sort(key=lambda x: x.reranked_score, reverse=True)
        return reranked
    
    async def _keyword_rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]]
    ) -> List[RerankedResult]:
        """Rerank based on keyword matching."""
        reranked = []
        
        for result in results:
            keyword_score = self._calculate_keyword_score(query, result['content'])
            score = keyword_score  # Pure keyword-based scoring
            
            reranked.append(RerankedResult(
                chunk_id=result['chunk_id'],
                content_type=result['content_type'],
                content=result['content'],
                metadata=result['metadata'],
                original_similarity=result['similarity'],
                reranked_score=score,
                reranking_reason=f"Keyword score: {keyword_score:.3f}"
            ))
        
        reranked.sort(key=lambda x: x.reranked_score, reverse=True)
        return reranked
    
    async def _metadata_rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]]
    ) -> List[RerankedResult]:
        """Rerank based on metadata relevance."""
        reranked = []
        
        for result in results:
            if result['metadata']:
                metadata_score = self._calculate_metadata_score(query, result['metadata'])
                score = metadata_score
            else:
                metadata_score = 0
                score = 0
            
            reranked.append(RerankedResult(
                chunk_id=result['chunk_id'],
                content_type=result['content_type'],
                content=result['content'],
                metadata=result['metadata'],
                original_similarity=result['similarity'],
                reranked_score=score,
                reranking_reason=f"Metadata score: {metadata_score:.3f}"
            ))
        
        reranked.sort(key=lambda x: x.reranked_score, reverse=True)
        return reranked
    
    async def _semantic_rerank(
        self, 
        query: str, 
        results: List[Dict[str, Any]]
    ) -> List[RerankedResult]:
        """Rerank based on semantic similarity (original scores)."""
        reranked = []
        
        for result in results:
            reranked.append(RerankedResult(
                chunk_id=result['chunk_id'],
                content_type=result['content_type'],
                content=result['content'],
                metadata=result['metadata'],
                original_similarity=result['similarity'],
                reranked_score=result['similarity'],
                reranking_reason="Semantic similarity (no reranking)"
            ))
        
        reranked.sort(key=lambda x: x.reranked_score, reverse=True)
        return reranked
    
    def _calculate_keyword_score(self, query: str, content: str) -> float:
        """Calculate keyword matching score between query and content."""
        if not query or not content:
            return 0.0
        
        # Normalize and tokenize
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        content_words = set(re.findall(r'\b\w+\b', content.lower()))
        
        if not query_words:
            return 0.0
        
        # Calculate intersection
        matches = query_words.intersection(content_words)
        
        # Score based on match ratio and content length
        match_ratio = len(matches) / len(query_words)
        
        # Boost for longer content (more comprehensive)
        length_factor = min(1.0, len(content) / 1000)  # Normalize to 1.0 at 1000 chars
        
        # Combine factors
        score = match_ratio * 0.7 + length_factor * 0.3
        
        return min(1.0, score)
    
    def _calculate_metadata_score(self, query: str, metadata: Dict[str, Any]) -> float:
        """Calculate metadata relevance score."""
        if not metadata:
            return 0.0
        
        score = 0.0
        query_lower = query.lower()
        
        # Check various metadata fields
        for key, value in metadata.items():
            if isinstance(value, str):
                value_lower = value.lower()
                if query_lower in value_lower:
                    score += 0.3  # Exact match
                elif any(word in value_lower for word in query_lower.split()):
                    score += 0.1  # Partial match
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, str) and query_lower in item.lower():
                        score += 0.2
        
        return min(1.0, score)
    
    def _calculate_content_type_score(self, query: str, content_type: str) -> float:
        """Calculate content type relevance score."""
        query_lower = query.lower()
        content_type_lower = content_type.lower()
        
        # Boost for character-related queries matching character content
        if any(word in query_lower for word in ['character', 'person', 'protagonist', 'hero', 'villain']):
            if 'character' in content_type_lower:
                return 0.3
        
        # Boost for setting-related queries
        if any(word in query_lower for word in ['setting', 'location', 'place', 'world', 'environment']):
            if 'setting' in content_type_lower:
                return 0.3
        
        # Boost for plot-related queries
        if any(word in query_lower for word in ['plot', 'story', 'narrative', 'conflict', 'theme']):
            if 'outline' in content_type_lower:
                return 0.3
        
        return 0.0
    
    def _generate_reranking_reason(
        self, 
        original_sim: float, 
        keyword_score: float, 
        metadata_score: float, 
        content_type_score: float
    ) -> str:
        """Generate human-readable explanation of reranking."""
        reasons = []
        
        if keyword_score > 0.1:
            reasons.append(f"keywords: {keyword_score:.3f}")
        if metadata_score > 0.1:
            reasons.append(f"metadata: {metadata_score:.3f}")
        if content_type_score > 0.1:
            reasons.append(f"content_type: {content_type_score:.3f}")
        
        if reasons:
            return f"Original: {original_sim:.3f}, Boosted by: {', '.join(reasons)}"
        else:
            return f"Original similarity: {original_sim:.3f} (no boost applied)"
