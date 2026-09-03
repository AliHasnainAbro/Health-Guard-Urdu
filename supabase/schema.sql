-- HealthGuard Urdu — Supabase schema (Step 3)
-- Knowledge base for RAG retrieval with pgvector embeddings.
-- NOTE: vector(384) must match the embedding model chosen in Step 4
-- (default pick: paraphrase-multilingual-MiniLM-L12-v2 → 384 dims).

-- Enable the pgvector extension
create extension if not exists vector;

-- Knowledge base table: one row per WHO EMRO Urdu health document/chunk
create table if not exists healthguard_kb (
    id bigserial primary key,
    title text not null,
    category text not null,          -- e.g. 'polio_vaccine', 'general_vaccine', 'home_remedy'
    content_urdu text not null,      -- the actual Urdu-language document content
    source_url text,                 -- WHO EMRO source reference
    is_direct_urdu_source boolean default false,  -- true if sourced in Urdu directly, false if translated
    embedding vector(384),           -- adjust dimension to match the embedding model in Step 4
    created_at timestamptz default now()
);

-- Index for fast similarity search (cosine distance)
create index if not exists healthguard_kb_embedding_idx
    on healthguard_kb
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);
