#!/bin/bash

# RAG System Setup Script for AI Story Writer
# This script sets up the PostgreSQL database with pgvector and installs dependencies

set -e

echo "🚀 Setting up RAG System for AI Story Writer..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama is not running. Please start Ollama and try again."
    exit 1
fi

echo "✅ Docker and Ollama are running"

# Pull the nomic-embed-text model for embeddings
echo "📥 Pulling nomic-embed-text embedding model..."
ollama pull nomic-embed-text

# Start PostgreSQL with pgvector
echo "🐘 Starting PostgreSQL with pgvector..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U story_user -d story_writer > /dev/null 2>&1; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL is ready"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements-rag.txt

echo ""
echo "🎉 RAG System setup complete!"
echo ""
echo "Next steps:"
echo "1. Test the connection: python src/presentation/cli/rag_cli.py test"
echo "2. List stories: python src/presentation/cli/rag_cli.py list"
echo "3. Index an existing story: python src/presentation/cli/rag_cli.py index --prompt-file Prompts/YourPrompt.txt --output-dir Stories/YourStory"
echo ""
echo "For help: python src/presentation/cli/rag_cli.py --help"
echo ""
echo "To stop PostgreSQL: docker-compose down"
