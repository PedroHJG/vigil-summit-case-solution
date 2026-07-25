-- ============================================================================
-- Vigil Summit — Migration 0004: RAG da base de conhecimento do evento
--
-- Aplicar no SQL Editor do Supabase (após a 0003).
-- Habilita a extensão pgvector e cria a tabela indexada por embeddings.
-- ============================================================================

-- Extensão de vetores (nativa do Supabase; basta habilitar)
create extension if not exists vector;

-- Um registro por chunk da base de conhecimento (seção do markdown).
-- embedding: vetor de 1024 dimensões (voyage-3.5, dimensão padrão).
create table if not exists event_knowledge (
  id           uuid primary key default gen_random_uuid(),
  chunk_index  int not null,                 -- ordem no documento (estável)
  heading      text not null,                -- título da seção (ex.: "3.3 Sessão 3 — ...")
  content      text not null,                -- texto completo do chunk
  tags         text[] not null default '{}', -- tags do markdown, p/ filtro/observabilidade
  embedding    vector(1024),
  updated_at   timestamptz not null default now(),
  unique (chunk_index)                       -- ingestão idempotente por posição
);

-- Com pouca dezena de chunks, um índice ANN (ivfflat/hnsw) não traz ganho e
-- ivfflat exige mais linhas para treinar bem — o scan sequencial é instantâneo.
-- Ao escalar a base, criar:
--   create index on event_knowledge using hnsw (embedding vector_cosine_ops);

-- RLS ligado sem policies: só a service key (backend) acessa. A busca por
-- similaridade é feita pelo backend via psycopg (operador de distância <=>),
-- o mesmo caminho já usado pela memória do agente.
alter table event_knowledge enable row level security;