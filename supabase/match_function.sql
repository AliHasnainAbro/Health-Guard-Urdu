create or replace function match_healthguard_kb (
  query_embedding vector(384),
  match_count int default 3
)
returns table (
  id bigint,
  title text,
  category text,
  content_urdu text,
  source_url text,
  is_direct_urdu_source boolean,
  similarity float
)
language sql stable
as $$
  select
    id, title, category, content_urdu, source_url, is_direct_urdu_source,
    1 - (embedding <=> query_embedding) as similarity
  from healthguard_kb
  order by embedding <=> query_embedding
  limit match_count;
$$;
