#!/bin/bash

# Embedding Model Migration Wrapper Script
# This script provides easy access to common migration scenarios

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATE_SCRIPT="$SCRIPT_DIR/migrate_embed.py"

# Function to show usage
show_usage() {
    echo "🚀 Embedding Model Migration Script"
    echo ""
    echo "Usage:"
    echo "  $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
echo "  fast        - Migrate to all-MiniLM-L6-v2 (384d, faster)"
echo "  accurate    - Migrate to nomic-embed-text (1536d, more accurate)"
echo "  custom      - Migrate to custom model"
echo "  dry-run     - Show what would be migrated without making changes"
echo "  analyze     - Analyze current database and show migration needs"
echo "  status      - Show migration history and status"
    echo ""
    echo "Examples:"
    echo "  $0 fast                    # Migrate to fast model"
    echo "  $0 accurate                # Migrate to accurate model"
    echo "  $0 custom ollama://bge-large-en  # Custom model"
    echo "  $0 dry-run                 # Show migration plan"
    echo "  $0 analyze                 # Analyze current state"
    echo ""
    echo "Options:"
    echo "  --skip-cleanup            # Skip cleanup of backup table"
    echo "  --help                    # Show this help"
}

# Function to run migration
run_migration() {
    local new_model="$1"
    local dry_run="$2"
    local skip_cleanup="$3"
    
    echo "🚀 Starting migration to: $new_model"
    
    local cmd="python3 $MIGRATE_SCRIPT --new-model \"$new_model\""
    
    if [ "$dry_run" = "true" ]; then
        cmd="$cmd --dry-run"
    fi
    
    if [ "$skip_cleanup" = "true" ]; then
        cmd="$cmd --skip-cleanup"
    fi
    
    echo "Running: $cmd"
    eval $cmd
}

# Function to analyze current state
analyze_current() {
    echo "🔍 Analyzing current database state..."
    python3 "$MIGRATE_SCRIPT" --new-model "ollama://nomic-embed-text" --dry-run
}

# Function to show migration status
show_migration_status() {
    echo "📊 Migration Status and History"
    echo "================================"
    
    # Check if PostgreSQL is running
    if ! docker compose ps postgres | grep -q "Up"; then
        echo "❌ PostgreSQL is not running. Start it with: docker compose up -d postgres"
        return 1
    fi
    
    # Query migration status
    docker compose exec -T postgres psql -U story_user -d story_writer -c "
        SELECT 
            id,
            migration_type,
            from_dimensions,
            to_dimensions,
            status,
            created_at,
            completed_at,
            error_message
        FROM migration_status 
        ORDER BY created_at DESC;
    " 2>/dev/null || echo "❌ Could not query migration status"
}

# Main script logic
case "${1:-}" in
    "fast")
        run_migration "ollama://all-MiniLM-L6-v2" "false" "${2:-false}"
        ;;
    "accurate")
        run_migration "ollama://nomic-embed-text" "false" "${2:-false}"
        ;;
    "custom")
        if [ -z "$2" ]; then
            echo "❌ Custom model requires model specification"
            echo "Example: $0 custom ollama://bge-large-en"
            exit 1
        fi
        run_migration "$2" "false" "${3:-false}"
        ;;
    "dry-run")
        # Use current model from config for dry-run
        if [ -f "config.md" ]; then
            current_model=$(grep -A 20 "infrastructure:" config.md | grep "embedding_model:" | head -1 | sed 's/.*embedding_model:\s*"//' | sed 's/".*//')
            if [ -n "$current_model" ]; then
                echo "🔍 Dry run with current model: $current_model"
                run_migration "$current_model" "true" "${2:-false}"
            else
                echo "❌ Could not determine current model from config.md"
                exit 1
            fi
        else
            echo "❌ config.md not found"
            exit 1
        fi
        ;;
            "analyze")
        analyze_current
        ;;
        "status")
        show_migration_status
        ;;
    "--help"|"-h"|"help")
        show_usage
        ;;
    "")
        show_usage
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac
