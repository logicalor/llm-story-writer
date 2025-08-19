#!/usr/bin/env python3
"""RAG Query CLI - Direct command-line interface to query the RAG system."""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Query the RAG system directly from command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all stories
  python rag_query_cli.py --list-stories
  
  # Get story summary
  python rag_query_cli.py --story 1 --summary
  
  # Search content in specific story
  python rag_query_cli.py --story 1 --search "character development"
  
  # Search with rule-based reranking for better results
  python rag_query_cli.py --story 1 --search "character development" --rerank
  
  # Search with model-based reranking (BGE-reranker-v2-m3)
  python rag_query_cli.py --story 1 --search "character development" --rerank --rerank-type model_based
  
  # Search with specific reranking strategy
  python rag_query_cli.py --story 1 --search "character development" --rerank --rerank-strategy keyword
  python rag_query_cli.py --story 1 --search "character development" --rerank --rerank-type model_based --rerank-strategy cross_encoder
  
  # Search across all stories
  python rag_query_cli.py --search "character development"
  
  # Query with AI model (requires story ID)
  python rag_query_cli.py --story 1 --query "What is the main conflict?"
  
  # Query with reranking
  python rag_query_cli.py --story 1 --query "What is the main conflict?" --rerank
  
  # Get content statistics
  python rag_query_cli.py --stats
  python rag_query_cli.py --story 1 --stats
  
  # Start interactive conversation mode
  python rag_query_cli.py --story 1 --interactive
  
  # Interactive mode with reranking
  python rag_query_cli.py --story 1 --interactive --rerank
        """
    )
    
    parser.add_argument("--list-stories", "-l", action="store_true", 
                       help="List all available stories")
    parser.add_argument("--story", "-s", type=int, 
                       help="Story ID to work with")
    parser.add_argument("--summary", action="store_true", 
                       help="Show story content summary")
    parser.add_argument("--stats", action="store_true", 
                       help="Show content statistics")
    parser.add_argument("--search", type=str, 
                       help="Search query to execute")
    parser.add_argument("--query", type=str, 
                       help="AI query question")
    parser.add_argument("--limit", type=int, default=10, 
                       help="Maximum results to return (default: 10)")
    parser.add_argument("--threshold", type=float, default=0.7, 
                       help="Similarity threshold (default: 0.7)")
    parser.add_argument("--content-type", type=str, 
                       help="Filter by content type")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Start interactive conversation mode")
    parser.add_argument("--rerank", action="store_true",
                       help="Use reranking to improve search result quality")
    parser.add_argument("--rerank-type", choices=["rule_based", "model_based"],
                       default="rule_based", help="Type of reranker to use (default: rule_based)")
    parser.add_argument("--rerank-strategy", choices=["hybrid", "keyword", "metadata", "semantic", "cross_encoder"],
                       default="hybrid", help="Reranking strategy to use (default: hybrid)")
    
    args = parser.parse_args()
    
    if not any([args.list_stories, args.summary, args.stats, args.search, args.query, args.interactive]):
        parser.print_help()
        return
    
    try:
        # Import required components
        from infrastructure.storage.pgvector_store import PgVectorStore
        from infrastructure.providers.ollama_embedding_provider import OllamaEmbeddingProvider
        from infrastructure.providers.ollama_provider import OllamaProvider
        from application.services.rag_service import RAGService
        from application.services.content_chunker import ContentChunker
        from application.services.rag_integration_service import RAGIntegrationService
        
        # Load configuration
        from config.config_loader import ConfigLoader
        from config.rag_config import RAGConfigLoader
        
        print("🚀 Initializing RAG system...")
        
        # Load configuration
        config_loader = ConfigLoader()
        rag_config_loader = RAGConfigLoader(config_loader)
        config = rag_config_loader.load_rag_config()
        
        # Initialize components
        embedding_provider = OllamaEmbeddingProvider(
            host=config.ollama_host,
            model=config.embedding_model_name
        )
        
        vector_store = PgVectorStore(config.connection_string)
        await vector_store.initialize()
        
        # Determine reranker type from CLI arguments
        reranker_type = "rule_based"  # Default
        if args.rerank:
            reranker_type = args.rerank_type
        
        rag_service = RAGService(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            similarity_threshold=config.similarity_threshold,
            max_context_chunks=config.max_context_chunks,
            use_reranker=args.rerank,  # Enable reranking only if --rerank flag is used
            reranker_type=reranker_type
        )
        
        content_chunker = ContentChunker(
            max_chunk_size=config.max_chunk_size,
            overlap_size=config.overlap_size
        )
        
        rag_integration = RAGIntegrationService(
            rag_service=rag_service,
            content_chunker=content_chunker
        )
        
        # Initialize Ollama provider for AI responses
        try:
            ollama_provider = OllamaProvider(host="127.0.0.1:11434")
            print("✅ Ollama provider initialized for AI responses")
        except Exception as e:
            print(f"⚠️ Warning: Ollama provider not available: {e}")
            ollama_provider = None
        
        print("✅ RAG system initialized successfully!")
        
        # Execute requested operations
        if args.list_stories:
            await list_stories(vector_store)
        
        if args.summary and args.story:
            await show_story_summary(rag_service, args.story)
        
        if args.stats:
            if args.story:
                await show_story_stats(rag_service, args.story)
            else:
                await show_all_stats(rag_service, vector_store)
        
        if args.search:
            if args.story:
                await search_story_content(rag_service, args.story, args.search, 
                                        args.limit, args.threshold, args.content_type, args.rerank, args.rerank_type, args.rerank_strategy)
            else:
                await search_all_content(rag_service, args.search, 
                                      args.limit, args.threshold, args.content_type, args.rerank, args.rerank_type, args.rerank_strategy)
        
        if args.query:
            if not args.story:
                print("❌ Error: --query requires --story to be specified")
                return
            await ai_query(rag_service, args.story, args.query, 
                         args.limit, args.threshold, args.content_type, ollama_provider, args.rerank, args.rerank_type, args.rerank_strategy)
        
        if args.interactive:
            if not args.story:
                print("❌ Error: --interactive requires --story to be specified")
                return
            await interactive_conversation(rag_service, args.story, args.limit, 
                                        args.threshold, args.content_type, ollama_provider, args.rerank, args.rerank_type, args.rerank_strategy)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if 'vector_store' in locals():
                await vector_store.close()
        except:
            pass

async def list_stories(vector_store):
    """List all available stories."""
    print("\n📚 Available Stories:")
    print("=" * 60)
    
    try:
        stories = await vector_store.list_stories()
        if not stories:
            print("No stories found in RAG system")
            return
        
        for story in stories:
            print(f"ID: {story['id']}")
            print(f"Name: {story['story_name']}")
            print(f"Prompt File: {story['prompt_file_name']}")
            print(f"Created: {story['created_at']}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Error listing stories: {e}")

async def show_story_summary(rag_service, story_id):
    """Show content summary for a specific story."""
    print(f"\n📖 Story Summary for ID {story_id}:")
    print("=" * 60)
    
    try:
        summary = await rag_service.get_story_summary(story_id)
        if not summary:
            print(f"No summary available for story {story_id}")
            return
        
        story_info = summary.get("story_info", {})
        content_counts = summary.get("content_counts", {})
        total_chunks = summary.get("total_chunks", 0)
        
        print(f"Name: {story_info.get('story_name', 'Unknown')}")
        print(f"Prompt File: {story_info.get('prompt_file_name', 'Unknown')}")
        print(f"Total Content Chunks: {total_chunks}")
        print("\nContent by Type:")
        
        for content_type, count in content_counts.items():
            if count > 0:
                print(f"  - {content_type}: {count} chunks")
                
    except Exception as e:
        print(f"❌ Error getting story summary: {e}")

async def show_story_stats(rag_service, story_id):
    """Show detailed statistics for a specific story."""
    print(f"\n📊 Content Statistics for Story {story_id}:")
    print("=" * 60)
    
    try:
        summary = await rag_service.get_story_summary(story_id)
        if not summary:
            print(f"No summary available for story {story_id}")
            return
        
        story_info = summary.get("story_info", {})
        content_counts = summary.get("content_counts", {})
        total_chunks = summary.get("total_chunks", 0)
        
        print(f"Name: {story_info.get('story_name', 'Unknown')}")
        print(f"Total Chunks: {total_chunks}")
        print("\nBreakdown by Type:")
        
        for content_type, count in content_counts.items():
            if count > 0:
                percentage = (count / total_chunks) * 100
                print(f"  - {content_type}: {count} chunks ({percentage:.1f}%)")
                
    except Exception as e:
        print(f"❌ Error getting story statistics: {e}")

async def show_all_stats(rag_service, vector_store):
    """Show statistics for all stories."""
    print("\n📈 Content Statistics for All Stories:")
    print("=" * 60)
    
    try:
        stories = await vector_store.list_stories()
        if not stories:
            print("No stories found in RAG system")
            return
        
        total_chunks_all = 0
        content_types_all = set()
        
        for story in stories:
            story_id = story['id']
            summary = await rag_service.get_story_summary(story_id)
            if summary:
                content_counts = summary.get("content_counts", {})
                total_chunks = summary.get("total_chunks", 0)
                total_chunks_all += total_chunks
                
                for content_type, count in content_counts.items():
                    if count > 0:
                        content_types_all.add(content_type)
                
                print(f"\nStory {story_id}: {story['story_name']}")
                print(f"  Total Chunks: {total_chunks}")
                for content_type, count in content_counts.items():
                    if count > 0:
                        print(f"  - {content_type}: {count}")
        
        print(f"\n📊 Overall Statistics:")
        print(f"  Total Stories: {len(stories)}")
        print(f"  Total Chunks: {total_chunks_all}")
        print(f"  Content Types: {', '.join(sorted(content_types_all))}")
        
    except Exception as e:
        print(f"❌ Error getting all statistics: {e}")

async def search_story_content(rag_service, story_id, query, limit, threshold, content_type, use_rerank=False, rerank_type="rule_based", rerank_strategy="hybrid"):
    """Search content within a specific story."""
    print(f"\n🔍 Searching Story {story_id} for: '{query}'")
    print(f"Limit: {limit}, Threshold: {threshold}")
    if content_type:
        print(f"Content Type: {content_type}")
    if use_rerank:
        print(f"Reranking: Enabled with {rerank_strategy} strategy")
    print("=" * 80)
    
    try:
        if use_rerank:
            results = await rag_service.search_similar_reranked(
                query=query,
                story_id=story_id,
                content_type=content_type,
                limit=limit,
                similarity_threshold=threshold,
                rerank_strategy=rerank_strategy
            )
        else:
            results = await rag_service.search_similar(
                query=query,
                story_id=story_id,
                content_type=content_type,
                limit=limit,
                similarity_threshold=threshold
            )
        
        if not results:
            print("❌ No relevant content found")
            return
        
        print(f"✅ Found {len(results)} relevant content chunks:")
        print("=" * 80)
        
        for i, (chunk_id, content_type, content, metadata, similarity) in enumerate(results, 1):
            print(f"\n📄 Chunk {i} (ID: {chunk_id}, Similarity: {similarity:.3f})")
            print(f"Type: {content_type}")
            if metadata:
                print(f"Metadata: {metadata}")
            print(f"Content: {content[:200]}{'...' if len(content) > 200 else ''}")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ Error searching content: {e}")

async def search_all_content(rag_service, query, limit, threshold, content_type, use_rerank=False, rerank_type="rule_based", rerank_strategy="hybrid"):
    """Search content across all stories."""
    print(f"\n🔍 Searching All Stories for: '{query}'")
    print(f"Limit: {limit}, Threshold: {threshold}")
    if content_type:
        print(f"Content Type: {content_type}")
    print("=" * 80)
    
    try:
        if use_rerank:
            results = await rag_service.search_similar_reranked(
                query=query,
                story_id=None,  # Search across all stories
                content_type=content_type,
                limit=limit,
                similarity_threshold=threshold,
                rerank_strategy=rerank_strategy
            )
        else:
            results = await rag_service.search_similar(
                query=query,
                story_id=None,  # Search across all stories
                content_type=content_type,
                limit=limit,
                similarity_threshold=threshold
            )
        
        if not results:
            print("❌ No relevant content found")
            return
        
        print(f"✅ Found {len(results)} relevant content chunks:")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            if len(result) == 5:
                # Single story search result
                chunk_id, content_type, content, metadata, similarity = result
                story_info = ""
            elif len(result) == 7:
                # Cross-story search result
                chunk_id, content_type, content, metadata, similarity, story_name, prompt_file = result
                story_info = f" (Story: {story_name}, File: {prompt_file})"
            else:
                print(f"⚠️ Unexpected result format: {len(result)} elements")
                continue
            
            print(f"\n📄 Chunk {i} (ID: {chunk_id}, Similarity: {similarity:.3f}){story_info}")
            print(f"Type: {content_type}")
            if metadata:
                print(f"Metadata: {metadata}")
            print(f"Content: {content[:200]}{'...' if len(content) > 200 else ''}")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ Error searching content: {e}")

async def show_mock_response(results, query):
    """Show a mock AI response when real AI is not available."""
    mock_response = f"Based on the {len(results)} content chunks found, here's what I can tell you about '{query}':\n\n"
    mock_response += "The content covers various aspects including:\n"
    
    content_types = set()
    for _, content_type, _, _, _ in results:
        content_types.add(content_type)
    
    for content_type in content_types:
        mock_response += f"- {content_type} information\n"
    
    mock_response += f"\nTotal similarity scores range from {min(r[4] for r in results):.3f} to {max(r[4] for r in results):.3f}"
    
    print("\n🤖 Mock AI Response:")
    print("=" * 80)
    print(mock_response)
    print("=" * 80)

async def ai_query(rag_service, story_id, query, limit, threshold, content_type, ollama_provider=None, use_rerank=False, rerank_type="rule_based", rerank_strategy="hybrid"):
    """Execute an AI query on RAG content."""
    print(f"\n🤖 AI Query: '{query}'")
    print(f"Story ID: {story_id}")
    print(f"Limit: {limit}, Threshold: {threshold}")
    if content_type:
        print(f"Content Type: {content_type}")
    print("=" * 80)
    
    try:
        # Search for relevant content
        if use_rerank:
            results = await rag_service.search_similar_reranked(
                query=query,
                story_id=story_id,
                content_type=content_type,
                limit=limit,
                similarity_threshold=threshold,
                rerank_strategy=rerank_strategy
            )
        else:
            results = await rag_service.search_similar(
                query=query,
                story_id=story_id,
                content_type=content_type,
                limit=limit,
                similarity_threshold=threshold
            )
        
        if not results:
            print("❌ No relevant content found for AI query")
            return
        
        print(f"📚 Found {len(results)} relevant content chunks")
        
        # Prepare context for the AI
        context_parts = []
        for chunk_id, content_type, content, metadata, similarity in results:
            context_parts.append(f"[{content_type.upper()}] (Similarity: {similarity:.3f})\n{content}")
        
        context = "\n\n".join(context_parts)
        
        # Create prompt for the AI
        ai_prompt = f"""Here's what I know about the story:

{context}

Question: {query}

Please provide a comprehensive answer based on the story information above. If the information doesn't fully address the question, say so and provide what you can from the available story details."""
        
        print(f"\n📝 AI Prompt ({len(ai_prompt)} characters):")
        print("-" * 40)
        print(ai_prompt[:500] + "..." if len(ai_prompt) > 500 else ai_prompt)
        print("-" * 40)
        
        # Try to get real AI response if provider is available
        if ollama_provider:
            try:
                print("\n🤖 Getting real AI response from Ollama...")
                
                # Create ModelConfig for the request
                from src.domain.value_objects.model_config import ModelConfig
                model_config = ModelConfig(
                    name="llama3:latest",
                    provider="ollama",
                    host="127.0.0.1:11434"
                )
                
                # Use Ollama to generate response
                ai_response = await ollama_provider.generate_text(
                    messages=[{"role": "user", "content": ai_prompt}],
                    model_config=model_config
                )
                
                print("\n🤖 Real AI Response:")
                print("=" * 80)
                print(ai_response)
                print("=" * 80)
                
            except Exception as e:
                print(f"⚠️ AI generation failed: {e}")
                print("Falling back to mock response...")
                await show_mock_response(results, query)
        else:
            print("\n⚠️ No AI provider available, showing mock response...")
            await show_mock_response(results, query)
        
        # Show source content summary
        content_types = set()
        for _, content_type, _, _, _ in results:
            content_types.add(content_type)
            
        print("\n📚 Source Content Summary:")
        print(f"- Total chunks used: {len(results)}")
        print(f"- Content types: {', '.join(content_types)}")
        print(f"- Average similarity: {sum(r[4] for r in results) / len(results):.3f}")
        
    except Exception as e:
        print(f"❌ Error in AI query: {e}")

async def interactive_conversation(rag_service, story_id, limit, threshold, content_type, ollama_provider=None, use_rerank=False, rerank_type="rule_based", rerank_strategy="hybrid"):
    """Interactive conversation mode with RAG-enhanced AI responses."""
    print(f"\n💬 Starting interactive conversation for Story ID: {story_id}")
    print("=" * 80)
    print("🤖 You can now have a conversation with the AI model!")
    print("📚 Each response will be enhanced with relevant story information.")
    print("💡 Type 'quit', 'exit', or 'bye' to end the conversation.")
    print("💡 Type 'help' for available commands.")
    print("💡 Type 'context' to see what story details are being used.")
    print("=" * 80)
    
    # Get story info
    try:
        summary = await rag_service.get_story_summary(story_id)
        story_name = summary.get("story_info", {}).get("story_name", f"Story {story_id}")
        print(f"📖 Story: {story_name}")
    except:
        story_name = f"Story {story_id}"
    
    # Initialize conversation history
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Goodbye! Thanks for chatting!")
                break
            
            if user_input.lower() == 'help':
                print("\n📚 Available Commands:")
                print("  - 'quit', 'exit', 'bye': End conversation")
                print("  - 'help': Show this help")
                print("  - 'context': Show current RAG context")
                print("  - 'clear': Clear conversation history")
                print("  - 'stats': Show story statistics")
                print("  - Any other text: Ask a question or continue conversation")
                continue
            
            if user_input.lower() == 'clear':
                conversation_history = []
                print("🧹 Conversation history cleared!")
                continue
            
            if user_input.lower() == 'stats':
                await show_story_stats(rag_service, story_id)
                continue
            
            if user_input.lower() == 'context':
                if conversation_history:
                    print(f"\n📚 Current conversation has {len(conversation_history)} messages")
                    print("Latest user message:", conversation_history[-1] if conversation_history else "None")
                else:
                    print("\n📚 No conversation history yet")
                continue
            
            print(f"\n🤖 AI is thinking...")
            
            # Search for relevant RAG content with lower threshold for interactive mode
            search_threshold = min(threshold, 0.3)  # Use lower threshold for interactive
            print(f"🔍 Searching with threshold: {search_threshold}")
            
            if use_rerank:
                results = await rag_service.search_similar_reranked(
                    query=user_input,
                    story_id=story_id,
                    content_type=content_type,
                    limit=limit,
                    similarity_threshold=search_threshold,
                    rerank_strategy=rerank_strategy
                )
            else:
                results = await rag_service.search_similar(
                    query=user_input,
                    story_id=story_id,
                    content_type=content_type,
                    limit=limit,
                    similarity_threshold=search_threshold
                )
            
            if not results:
                print("❌ No relevant story information found for your question")
                print(f"💡 Tried threshold: {search_threshold}, limit: {limit}")
                print("💡 Try rephrasing or ask about something else!")
                continue
            
            print(f"✅ Found {len(results)} relevant chunks")
            
            # Debug: Show what was found
            if len(results) <= 3:  # Only show full results for small numbers
                print("\n📚 Found chunks:")
                for i, (chunk_id, content_type, content, metadata, similarity) in enumerate(results, 1):
                    print(f"  {i}. {content_type} (similarity: {similarity:.3f})")
                    print(f"     Preview: {content[:100]}...")
            
            # Prepare context for the AI
            context_parts = []
            for chunk_id, content_type, content, metadata, similarity in results:
                context_parts.append(f"[{content_type.upper()}] (Similarity: {similarity:.3f})\n{content}")
            
            context = "\n\n".join(context_parts)
            
            # Create conversation-aware prompt
            if conversation_history:
                # Build conversation context
                conv_context = "\n".join([
                    f"{'User' if i % 2 == 0 else 'Assistant'}: {msg}" 
                    for i, msg in enumerate(conversation_history[-6:])  # Last 6 messages
                ])
                
                ai_prompt = f"""You are having a conversation with a user about their story. Here's the conversation so far:

{conv_context}

User: {user_input}

Here's what I know about their story:

{context}

Please provide a helpful, conversational response that:
1. Answers the user's question based on the story information
2. Maintains the conversation flow naturally
3. References specific details from the story when relevant
4. If the story information doesn't fully address the question, say so and provide what you can

Assistant:"""
            else:
                ai_prompt = f"""You are having a conversation with a user about their story. They've asked:

{user_input}

Here's what I know about their story:

{context}

Please provide a helpful, conversational response that:
1. Answers the user's question based on the story information
2. References specific details from the story when relevant
3. If the story information doesn't fully address the question, say so and provide what you can

Assistant:"""
            
            # Try to get real AI response if provider is available
            if ollama_provider:
                try:
                    # Create ModelConfig for the request
                    from src.domain.value_objects.model_config import ModelConfig
                    model_config = ModelConfig(
                        name="llama3:latest",
                        provider="ollama",
                        host="127.0.0.1:11434"
                    )
                    
                    # Use Ollama to generate response
                    ai_response = await ollama_provider.generate_text(
                        messages=[{"role": "user", "content": ai_prompt}],
                        model_config=model_config
                    )
                    
                    print(f"\n🤖 AI: {ai_response}")
                    
                    # Add to conversation history
                    conversation_history.append(user_input)
                    conversation_history.append(ai_response)
                    
                except Exception as e:
                    print(f"⚠️ AI generation failed: {e}")
                    print("💡 Try asking a different question or check if Ollama is running.")
                    continue
            else:
                print("\n⚠️ No AI provider available. Please install and run Ollama to use interactive mode.")
                break
            
            # Show RAG context summary (brief)
            content_types = set()
            for _, content_type, _, _, _ in results:
                content_types.add(content_type)
            
            print(f"\n📚 [RAG Context: {len(results)} chunks, types: {', '.join(content_types)}]")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Thanks for chatting!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("💡 Try asking a different question or type 'help' for commands.")

if __name__ == "__main__":
    asyncio.run(main())
