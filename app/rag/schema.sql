create extension if not exists vector;

create table if not exists documents (
    page_id text primary key,
    source_type text not null default 'notion',
    title text not null,
    url text,
    content_hash text not null,
    last_synced_at timestamptz not null default now()
);

create table if not exists chunks (
    id bigserial primary key,
    page_id text not null references documents (page_id) on delete cascade,
    chunk_index int not null,
    heading_path text,
    content text not null,
    embedding vector(3072),
    created_at timestamptz not null default now(),
    unique (page_id, chunk_index)
);

create index if not exists chunks_page_id_idx on chunks (page_id);

-- An ANN index (ivfflat/hnsw) is worth adding once the corpus is large enough
-- for exact search to matter. Skipped for now — not needed at this scale.

alter table chunks add column if not exists content_tsv tsvector
    generated always as (to_tsvector('english', content)) stored;

create index if not exists chunks_content_tsv_idx on chunks using gin (content_tsv);

-- Hybrid search: fuses vector similarity and keyword (full-text) ranking via
-- Reciprocal Rank Fusion. Runs both searches and the fusion server-side in one
-- round trip, rather than merging two separate retrievers in application code.
create or replace function hybrid_search(
    query_text text,
    query_embedding vector(3072),
    match_count int default 25,
    rrf_k int default 50
)
returns table (
    chunk_id bigint,
    page_id text,
    title text,
    url text,
    heading_path text,
    content text,
    score float
)
language sql as $$
    with semantic as (
        select c.id, row_number() over (order by c.embedding <=> query_embedding) as rank
        from chunks c
        order by c.embedding <=> query_embedding
        limit match_count * 2
    ),
    keyword as (
        select c.id, row_number() over (order by ts_rank(c.content_tsv, websearch_to_tsquery('english', query_text)) desc) as rank
        from chunks c
        where c.content_tsv @@ websearch_to_tsquery('english', query_text)
        limit match_count * 2
    ),
    fused as (
        select
            coalesce(s.id, k.id) as id,
            (1.0 / (rrf_k + coalesce(s.rank, 1000000)) + 1.0 / (rrf_k + coalesce(k.rank, 1000000))) as score
        from semantic s
        full outer join keyword k on s.id = k.id
    )
    select c.id as chunk_id, c.page_id, d.title, d.url, c.heading_path, c.content, f.score
    from fused f
    join chunks c on c.id = f.id
    join documents d on d.page_id = c.page_id
    order by f.score desc
    limit match_count;
$$;
