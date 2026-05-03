"""CLI tool for managing the RAG system.

This CLI now uses the rag-query tool via subprocess instead of direct RAGService calls.
"""

import asyncio
import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class RAGCLI:
    """Command-line interface for RAG system management using rag-query tool."""

    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None

    def _run_rag_query(self, operation: str, name: str, **kwargs) -> Dict[str, Any]:
        """Run the rag_query.py tool via subprocess.

        Args:
            operation: 'index' or 'query'
            name: Story name
            **kwargs: Additional arguments for the operation

        Returns:
            Parsed JSON response from the tool
        """
        cmd = [
            sys.executable,
            "-m",
            "tools.rag_query",
            "--operation",
            operation,
            "--name",
            name,
        ]

        # Add optional arguments
        for key, value in kwargs.items():
            if value is not None:
                arg_name = f"--{key.replace('_', '-')}"
                cmd.extend([arg_name, str(value)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"rag_query failed: {e.stderr}")
            raise RuntimeError(f"rag_query tool failed: {e.stderr}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse rag_query output: {e}")
            raise RuntimeError(f"Invalid JSON from rag_query: {e}")

    async def initialize(self):
        """Initialize the RAG system (no-op for ChromaDB-based system)."""
        # ChromaDB is file-based, no initialization needed
        print("RAG system initialized successfully (ChromaDB mode)!")
        return True

    async def test_connection(self):
        """Test ChromaDB connection by running a dummy query."""
        print("Testing ChromaDB connection...")

        try:
            # Test by running a query on a dummy story (will return empty results)
            self._run_rag_query(
                operation="query",
                name="__test_connection__",
                query="test",
                n_results=1,
            )
            print("✓ ChromaDB connection: OK")
        except Exception as e:
            print(f"✗ ChromaDB connection: ERROR - {e}")

    async def list_stories(self):
        """List all stories in ChromaDB.

        Note: ChromaDB collections are created on-demand, so we list
        collections that match the stories-* pattern.
        """
        import os

        chromadb_dir = os.environ.get("CHROMADB_DIR", ".chromadb")

        try:
            # List ChromaDB collections by looking at the directory
            chromadb_path = Path(chromadb_dir)
            if not chromadb_path.exists():
                print("No stories found (ChromaDB directory does not exist)")
                return

            # ChromaDB stores collections as subdirectories
            collections = [
                d.name
                for d in chromadb_path.iterdir()
                if d.is_dir() and d.name.startswith("stories-")
            ]

            if not collections:
                print("No stories found in ChromaDB")
                return

            print(f"Found {len(collections)} stories:")
            print("-" * 80)

            for collection in sorted(collections):
                story_name = collection.replace("stories-", "")
                print(f"Story: {story_name}")
                print("-" * 80)

        except Exception as e:
            print(f"Failed to list stories: {e}")

    async def index_story(self, prompt_file_path: str, output_dir: str):
        """Index an existing story from output directory using rag-query tool."""
        prompt_path = Path(prompt_file_path)
        output_path = Path(output_dir)

        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return

        if not output_path.exists():
            print(f"Output directory not found: {output_dir}")
            return

        try:
            story_name = prompt_path.stem
            print(f"Indexing story '{story_name}' from {prompt_file_path}...")

            indexing_results: Dict[str, int] = {}

            # Index chapter files
            if output_path.exists():
                chapter_files = list(output_path.glob("Chapter*.md"))
                for chapter_file in chapter_files:
                    try:
                        chapter_content = chapter_file.read_text(encoding="utf-8")
                        chapter_number = self._extract_chapter_number(chapter_file.name)

                        doc_id = f"chapter-{chapter_number}"
                        self._run_rag_query(
                            operation="index",
                            name=story_name,
                            doc_id=doc_id,
                            content=chapter_content,
                            content_type="chapter",
                            chapter_num=chapter_number,
                        )
                        indexing_results[f"Chapter {chapter_number}"] = 1

                    except Exception as e:
                        logger.error(
                            f"Failed to index chapter file {chapter_file}: {e}"
                        )

                # Index character files
                character_files = list(output_path.glob("*Character*.md"))
                for char_file in character_files:
                    try:
                        char_content = char_file.read_text(encoding="utf-8")
                        character_name = char_file.stem.replace("Character", "").strip()

                        doc_id = f"character-{character_name.lower().replace(' ', '-')}"
                        self._run_rag_query(
                            operation="index",
                            name=story_name,
                            doc_id=doc_id,
                            content=char_content,
                            content_type="character",
                        )
                        indexing_results[f"Character: {character_name}"] = 1

                    except Exception as e:
                        logger.error(f"Failed to index character file {char_file}: {e}")

            print("Indexing completed!")
            print("Results:")
            for item, count in indexing_results.items():
                print(f"  {item}: {count} chunks")

        except Exception as e:
            print(f"Failed to index story: {e}")

    def _extract_chapter_number(self, filename: str) -> int:
        """Extract chapter number from filename."""
        import re

        match = re.search(r"Chapter\s*(\d+)", filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 1  # Default to chapter 1 if no number found

    async def search_content(
        self, prompt_file_path: str, query: str, content_type: Optional[str] = None
    ):
        """Search for content in a story using rag-query tool."""
        prompt_path = Path(prompt_file_path)

        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return

        try:
            story_name = prompt_path.stem
            print(f"Searching for: '{query}'")
            if content_type:
                print(f"Content type: {content_type}")

            result = self._run_rag_query(
                operation="query",
                name=story_name,
                query=query,
                content_type=content_type,
                n_results=10,
            )

            results = result.get("results", [])

            if not results:
                print("No results found")
                return

            print(f"Found {len(results)} results:")
            print("-" * 80)

            for i, item in enumerate(results, 1):
                doc_id = item.get("doc_id", "unknown")
                score = item.get("score", 0.0)
                excerpt = item.get("excerpt", "")
                metadata = item.get("metadata", {})

                print(f"Result {i} (ID: {doc_id}, Score: {score:.3f})")
                if metadata:
                    print(f"Metadata: {metadata}")
                print(f"Content: {excerpt[:200]}...")
                print("-" * 80)

        except Exception as e:
            print(f"Failed to search content: {e}")

    async def get_context(
        self,
        prompt_file_path: str,
        chapter_number: int,
        scene_number: Optional[int] = None,
    ):
        """Get generation context for a chapter/scene using rag-query tool."""
        prompt_path = Path(prompt_file_path)

        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return

        try:
            story_name = prompt_path.stem
            print(f"Getting context for Chapter {chapter_number}")
            if scene_number:
                print(f"Scene {scene_number}")

            # Build a context query based on chapter/scene
            query = f"chapter {chapter_number}"
            if scene_number:
                query += f" scene {scene_number}"

            result = self._run_rag_query(
                operation="query",
                name=story_name,
                query=query,
                n_results=10,
            )

            results = result.get("results", [])

            if not results:
                print("No context found")
                return

            print("Context retrieved:")
            print("=" * 80)
            for item in results:
                excerpt = item.get("excerpt", "")
                metadata = item.get("metadata", {})
                content_type = metadata.get("content_type", "unknown")
                print(f"\n[{content_type.upper()}]")
                print(excerpt[:500])
                print("-" * 40)
            print("=" * 80)

        except Exception as e:
            print(f"Failed to get context: {e}")

    async def get_story_summary(self, prompt_file_path: str):
        """Get a summary of a story's indexed content."""
        prompt_path = Path(prompt_file_path)

        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return

        try:
            story_name = prompt_path.stem
            print(f"Getting summary for story: {story_name}")

            # Query for different content types
            content_types = ["outline", "chapter", "character", "setting", "recap"]
            content_counts: Dict[str, int] = {}

            for content_type in content_types:
                try:
                    result = self._run_rag_query(
                        operation="query",
                        name=story_name,
                        query=content_type,
                        content_type=content_type,
                        n_results=100,
                    )
                    content_counts[content_type] = len(result.get("results", []))
                except Exception:
                    content_counts[content_type] = 0

            total_chunks = sum(content_counts.values())

            print("Story Summary:")
            print("=" * 80)
            print(f"Story Name: {story_name}")
            print()

            if content_counts:
                print("Content Counts:")
                for content_type, count in content_counts.items():
                    print(f"  {content_type}: {count}")
                print()

            print(f"Total Content Chunks: {total_chunks}")
            print("=" * 80)

        except Exception as e:
            print(f"Failed to get story summary: {e}")

    async def close(self):
        """Close the RAG system (no-op for ChromaDB)."""
        pass


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="RAG System Management CLI")
    parser.add_argument(
        "command",
        choices=["test", "list", "index", "search", "context", "summary"],
        help="Command to execute",
    )

    parser.add_argument("--prompt-file", "-p", help="Path to prompt file")
    parser.add_argument("--output-dir", "-o", help="Path to output directory")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--content-type", "-t", help="Content type filter")
    parser.add_argument("--chapter", "-c", type=int, help="Chapter number")
    parser.add_argument("--scene", "-s", type=int, help="Scene number")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Initialize CLI
    cli = RAGCLI()

    try:
        if not await cli.initialize():
            return

        # Execute command
        if args.command == "test":
            await cli.test_connection()

        elif args.command == "list":
            await cli.list_stories()

        elif args.command == "index":
            if not args.prompt_file or not args.output_dir:
                print("index command requires --prompt-file and --output-dir")
                return
            await cli.index_story(args.prompt_file, args.output_dir)

        elif args.command == "search":
            if not args.prompt_file or not args.query:
                print("search command requires --prompt-file and --query")
                return
            await cli.search_content(args.prompt_file, args.query, args.content_type)

        elif args.command == "context":
            if not args.prompt_file or not args.chapter:
                print("context command requires --prompt-file and --chapter")
                return
            await cli.get_context(args.prompt_file, args.chapter, args.scene)

        elif args.command == "summary":
            if not args.prompt_file:
                print("summary command requires --prompt-file")
                return
            await cli.get_story_summary(args.prompt_file)

    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main())
