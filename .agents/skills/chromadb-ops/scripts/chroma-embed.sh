#!/usr/bin/env bash
#
# .agents/skills/chromadb-ops/scripts/chroma-embed.sh COLLECTION SOURCE_FILE [--id ID]
#
# Payload-builder for ChromaDB (MCP-only — no direct CLI access).
# Reads SOURCE_FILE and outputs a JSON payload the agent passes to:
#   chroma_add_documents / chroma_update_documents MCP tools.
#
# Exit codes:
#   0 = payload generated
#   1 = missing args or file not found
#
# Stdout: JSON payload
#

set -euo pipefail

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
if [[ $# -lt 2 ]]; then
    printf "Usage: %s COLLECTION SOURCE_FILE [--id ID]\n" "$0" >&2
    exit 1
fi

COLLECTION="$1"
SOURCE_FILE="$2"
shift 2

CUSTOM_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --id)
            CUSTOM_ID="${2:-}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Validate source file
# ---------------------------------------------------------------------------
if [[ ! -f "$SOURCE_FILE" ]]; then
    printf "Error: source file not found: %s\n" "$SOURCE_FILE" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Generate document ID
# ---------------------------------------------------------------------------
if [[ -n "$CUSTOM_ID" ]]; then
    DOC_ID="$CUSTOM_ID"
else
    # Slugify: COLLECTION-basename (lowercase, spaces/_→hyphens, strip other specials)
    BASENAME=$(basename "$SOURCE_FILE" .md \
        | tr '[:upper:]' '[:lower:]' \
        | tr -s ' _' '-' \
        | tr -dc 'a-z0-9-')
    DOC_ID="${COLLECTION}-${BASENAME}"
fi

# ---------------------------------------------------------------------------
# Read content and output JSON payload
# ---------------------------------------------------------------------------
CONTENT=$(cat "$SOURCE_FILE")
INDEXED_AT=$(date '+%Y-%m-%d')

jq -n \
    --arg collection "$COLLECTION" \
    --arg id "$DOC_ID" \
    --arg document "$CONTENT" \
    --arg source_file "$SOURCE_FILE" \
    --arg indexed_at "$INDEXED_AT" \
    '{
        collection: $collection,
        id: $id,
        document: $document,
        metadata: {
            source_file: $source_file,
            indexed_at: $indexed_at
        }
    }'

exit 0
