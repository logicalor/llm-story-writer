"""Content chunking service for breaking down large text into manageable chunks."""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContentChunk:
    """Represents a chunk of content with metadata."""
    content: str
    chunk_type: str
    chunk_subtype: Optional[str] = None
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    chapter_number: Optional[int] = None
    scene_number: Optional[int] = None


class ContentChunker:
    """Service for chunking large text content into semantic pieces."""
    
    def __init__(self, max_chunk_size: int = 1000, overlap_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
    
    def chunk_text(
        self,
        text: str,
        chunk_type: str,
        chunk_subtype: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None
    ) -> List[ContentChunk]:
        """Chunk text into semantic pieces."""
        if len(text) <= self.max_chunk_size:
            # Text is small enough, return as single chunk
            return [ContentChunk(
                content=text,
                chunk_type=chunk_type,
                chunk_subtype=chunk_subtype,
                title=title,
                metadata=metadata,
                chapter_number=chapter_number,
                scene_number=scene_number
            )]
        
        # Split by paragraphs first
        paragraphs = self._split_by_paragraphs(text)
        
        # If paragraphs are still too large, split by sentences
        if any(len(p) > self.max_chunk_size for p in paragraphs):
            paragraphs = self._split_by_sentences(text)
        
        # Create chunks from paragraphs
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= self.max_chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk.strip(),
                        chunk_type,
                        chunk_subtype,
                        title,
                        metadata,
                        chapter_number,
                        scene_number
                    ))
                current_chunk = paragraph + "\n\n"
        
        # Add the last chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk.strip(),
                chunk_type,
                chunk_subtype,
                title,
                metadata,
                chapter_number,
                scene_number
            ))
        
        # Add overlap between chunks for context
        if len(chunks) > 1 and self.overlap_size > 0:
            chunks = self._add_overlap(chunks)
        
        return chunks
    
    def chunk_chapter(
        self,
        chapter_content: str,
        chapter_number: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ContentChunk]:
        """Chunk chapter content into scenes or logical sections."""
        # Try to split by scene markers first
        scenes = self._split_by_scenes(chapter_content)
        
        if len(scenes) > 1:
            # Chapter has multiple scenes
            chunks = []
            for i, scene in enumerate(scenes):
                scene_metadata = metadata.copy() if metadata else {}
                scene_metadata["scene_number"] = i + 1
                
                scene_chunks = self.chunk_text(
                    scene,
                    "scene",
                    "chapter_content",
                    f"{title} - Scene {i + 1}" if title else f"Scene {i + 1}",
                    scene_metadata,
                    chapter_number,
                    i + 1
                )
                chunks.extend(scene_chunks)
            
            return chunks
        else:
            # Single scene chapter
            return self.chunk_text(
                chapter_content,
                "scene",
                "chapter_content",
                title,
                metadata,
                chapter_number,
                1
            )
    
    def chunk_character_sheet(
        self,
        character_content: str,
        character_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ContentChunk]:
        """Chunk character sheet content into logical sections."""
        # Split by common character sheet sections
        sections = self._split_character_sections(character_content)
        
        chunks = []
        for section_name, section_content in sections:
            section_metadata = metadata.copy() if metadata else {}
            section_metadata["character_name"] = character_name
            section_metadata["section"] = section_name
            
            section_chunks = self.chunk_text(
                section_content,
                "character",
                section_name.lower(),
                f"{character_name} - {section_name}",
                section_metadata
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def chunk_setting_description(
        self,
        setting_content: str,
        location_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ContentChunk]:
        """Chunk setting description content."""
        setting_metadata = metadata.copy() if metadata else {}
        setting_metadata["location"] = location_name
        
        return self.chunk_text(
            setting_content,
            "setting",
            "description",
            f"Setting: {location_name}",
            setting_metadata
        )
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs."""
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences."""
        # Split by sentence endings followed by space
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_by_scenes(self, text: str) -> List[str]:
        """Split chapter content by scene markers."""
        # Common scene markers
        scene_markers = [
            r'\n\s*Scene\s+\d+',
            r'\n\s*---\s*\n',
            r'\n\s*\*\*\*\s*\n',
            r'\n\s*Chapter\s+\d+',
            r'\n\s*Part\s+\d+'
        ]
        
        # Try to find scene breaks
        for marker in scene_markers:
            if re.search(marker, text, re.IGNORECASE):
                scenes = re.split(marker, text, flags=re.IGNORECASE)
                return [s.strip() for s in scenes if s.strip()]
        
        # No scene markers found, return as single scene
        return [text]
    
    def _split_character_sections(self, text: str) -> List[tuple]:
        """Split character sheet into logical sections."""
        # Common character sheet sections
        section_patterns = [
            (r'Appearance[:\s]*', 'Appearance'),
            (r'Personality[:\s]*', 'Personality'),
            (r'Background[:\s]*', 'Background'),
            (r'Motivation[:\s]*', 'Motivation'),
            (r'Goals[:\s]*', 'Goals'),
            (r'Relationships[:\s]*', 'Relationships'),
            (r'Skills[:\s]*', 'Skills'),
            (r'History[:\s]*', 'History')
        ]
        
        sections = []
        current_section = "General"
        current_content = ""
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new section
            section_found = False
            for pattern, section_name in section_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    if current_content:
                        sections.append((current_section, current_content.strip()))
                    current_section = section_name
                    current_content = line + "\n"
                    section_found = True
                    break
            
            if not section_found:
                current_content += line + "\n"
        
        # Add the last section
        if current_content:
            sections.append((current_section, current_content.strip()))
        
        return sections
    
    def _create_chunk(
        self,
        content: str,
        chunk_type: str,
        chunk_subtype: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None
    ) -> ContentChunk:
        """Create a content chunk with the given parameters."""
        return ContentChunk(
            content=content,
            chunk_type=chunk_type,
            chunk_subtype=chunk_subtype,
            title=title,
            metadata=metadata,
            chapter_number=chapter_number,
            scene_number=scene_number
        )
    
    def _add_overlap(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """Add overlap between chunks for better context."""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # Add overlap from previous chunk
                overlap_start = max(0, len(chunk.content) - self.overlap_size)
                overlap_text = chunk.content[overlap_start:]
                
                # Find the last complete sentence in the overlap
                sentences = self._split_by_sentences(overlap_text)
                if sentences:
                    overlap_text = sentences[-1]
                
                # Add overlap to the beginning of current chunk
                chunk.content = f"[Previous context: {overlap_text}]\n\n{chunk.content}"
            
            if i < len(chunks) - 1:
                # Add overlap to next chunk
                overlap_end = min(self.overlap_size, len(chunk.content))
                overlap_text = chunk.content[:overlap_end]
                
                # Find the first complete sentence in the overlap
                sentences = self._split_by_sentences(overlap_text)
                if sentences:
                    overlap_text = sentences[0]
                
                # Add overlap to the end of current chunk
                chunk.content = f"{chunk.content}\n\n[Next context: {overlap_text}]"
            
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks
