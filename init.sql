-- Initialize pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Stories table (one per story)
CREATE TABLE stories (
    id SERIAL PRIMARY KEY,
    story_name VARCHAR(255) UNIQUE NOT NULL,
    prompt_file_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content chunks table (for all story content)
CREATE TABLE content_chunks (
    id SERIAL PRIMARY KEY,
    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL, -- 'character', 'setting', 'event', 'outline', 'scene'
    content_subtype VARCHAR(50), -- 'history', 'summary', 'dialogue', etc.
    title VARCHAR(255),
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1536), -- Adjust dimension based on your embedding model
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chapter_number INTEGER,
    scene_number INTEGER
);

-- Indexes for performance
CREATE INDEX idx_content_chunks_story_id ON content_chunks(story_id);
CREATE INDEX idx_content_chunks_content_type ON content_chunks(content_type);
CREATE INDEX idx_content_chunks_chapter_scene ON content_chunks(chapter_number, scene_number);
CREATE INDEX idx_content_chunks_created_at ON content_chunks(created_at);

-- Vector similarity indexes
CREATE INDEX idx_content_chunks_embedding_hnsw ON content_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_content_chunks_embedding_ivfflat ON content_chunks USING ivfflat (embedding vector_cosine_ops);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_stories_updated_at BEFORE UPDATE ON stories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for better performance on common queries
CREATE INDEX idx_content_chunks_metadata_gin ON content_chunks USING GIN (metadata);
CREATE INDEX idx_content_chunks_content_type_subtype ON content_chunks(content_type, content_subtype);
