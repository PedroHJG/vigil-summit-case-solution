"""RAG da base de conhecimento do evento (Voyage embeddings + pgvector).

Fonte: backend/knowledge/vigil_summit_kb.md — um markdown onde cada seção
`##`/`###` é um chunk autocontido, terminando numa linha `tags: ...`.

Duas responsabilidades:
- `ingest()`  : (re)indexa o markdown na tabela event_knowledge (Supabase).
                Chamado pelo script scripts/ingest_knowledge.py.
- `search()`  : busca semântica usada pela tool consultar_conteudo_evento.

Os embeddings e a busca por similaridade de cosseno vão via psycopg direto
(DATABASE_URL / session pooler) — o mesmo caminho já usado pela memória do
agente —, formatando o vetor como literal pgvector. Isso evita depender de
cast implícito de array→vector do PostgREST.
"""

import logging
import re
from pathlib import Path

import psycopg

from core.config import get_settings

logger = logging.getLogger(__name__)

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "vigil_summit_kb.md"


# =============================================================================
# Chunking do markdown
# =============================================================================

def _clean(text: str) -> str:
    """Remove escapes de markdown e linhas separadoras (\\--- / ---)."""
    text = re.sub(r"^\s*\\?-{3,}\s*$", "", text, flags=re.MULTILINE)
    # tira a barra de escapes tipo \*  \&  \|  \.  \-
    text = re.sub(r"\\([*&|.\-])", r"\1", text)
    return text


def parse_chunks(md_text: str) -> list[dict]:
    """Divide o markdown em chunks (um por seção ##/### que tenha `tags:`).

    Retorna [{heading, content, tags}]. A introdução e headings sem corpo
    (ex.: "## 3. Conteúdo Programático", cujo conteúdo real está nas 3.x)
    não têm `tags:` e são descartados naturalmente.
    """
    md_text = _clean(md_text)
    blocks = re.split(r"\n(?=#{2,3} )", md_text)

    chunks: list[dict] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m_tags = re.search(r"`?tags:\s*([^`\n]+)`?", block)
        if not m_tags:
            continue

        tags = [t.strip() for t in m_tags.group(1).split(",") if t.strip()]
        heading = re.sub(r"^#{2,3}\s*", "", block.splitlines()[0]).strip()
        content = block[: m_tags.start()].strip()
        chunks.append({"heading": heading, "content": content, "tags": tags})

    return chunks


# =============================================================================
# Embeddings (Voyage)
# =============================================================================

def _embeddings():
    from langchain_voyageai import VoyageAIEmbeddings

    settings = get_settings()
    if not settings.voyage_api_key:
        raise RuntimeError("VOYAGE_API_KEY não configurada.")
    return VoyageAIEmbeddings(
        model=settings.voyage_model, api_key=settings.voyage_api_key
    )


def _vector_literal(vec: list[float]) -> str:
    """Formata o vetor como literal aceito pelo tipo vector do pgvector."""
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


# =============================================================================
# Ingestão (re-sincroniza a tabela com o arquivo)
# =============================================================================

def ingest() -> int:
    """Reindexa a base de conhecimento. Retorna o nº de chunks indexados.

    Estratégia simples e idempotente: apaga tudo e reinsere numa transação —
    com poucas dezenas de chunks é trivial e garante sincronia exata com o md
    (inclusive quando uma seção é removida).
    """
    settings = get_settings()
    chunks = parse_chunks(KB_PATH.read_text(encoding="utf-8"))
    if not chunks:
        raise RuntimeError(f"Nenhum chunk extraído de {KB_PATH}")

    # O heading entra no texto embedado: dá contexto e melhora o retrieval.
    texts = [f"{c['heading']}\n\n{c['content']}" for c in chunks]
    vectors = _embeddings().embed_documents(texts)

    with psycopg.connect(settings.database_url) as conn:
        with conn.transaction():
            conn.execute("delete from event_knowledge")
            for i, (c, v) in enumerate(zip(chunks, vectors)):
                conn.execute(
                    """
                    insert into event_knowledge
                        (chunk_index, heading, content, tags, embedding, updated_at)
                    values (%s, %s, %s, %s, %s::vector, now())
                    """,
                    (i, c["heading"], c["content"], c["tags"], _vector_literal(v)),
                )
    logger.info("Base de conhecimento reindexada: %d chunks.", len(chunks))
    return len(chunks)


# =============================================================================
# Busca semântica (usada pela tool do agente)
# =============================================================================

def search(pergunta: str, top_k: int | None = None) -> list[dict]:
    """Retorna os chunks mais relevantes p/ a pergunta (ordenados por similaridade)."""
    settings = get_settings()
    top_k = top_k or settings.rag_top_k
    qvec = _embeddings().embed_query(pergunta)
    literal = _vector_literal(qvec)

    with psycopg.connect(settings.database_url) as conn:
        rows = conn.execute(
            """
            select heading, content, tags,
                   1 - (embedding <=> %s::vector) as similarity
            from event_knowledge
            where embedding is not null
            order by embedding <=> %s::vector
            limit %s
            """,
            (literal, literal, top_k),
        ).fetchall()

    return [
        {"heading": r[0], "content": r[1], "tags": r[2], "similarity": float(r[3])}
        for r in rows
    ]