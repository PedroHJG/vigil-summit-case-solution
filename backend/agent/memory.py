"""Memória de conversa gerenciada nativamente pelo LangChain.

Usa PostgresChatMessageHistory (langchain-postgres) persistindo no próprio
Postgres do Supabase, na tabela `langchain_chat_history` (criada na migration
0001 e garantida de forma idempotente em ensure_history_table()).

Cada conversa (tabela `conversations`) possui um `session_id` UUID que é a
chave do histórico aqui.
"""

import logging
import weakref

import psycopg
from langchain_postgres import PostgresChatMessageHistory

from core.config import get_settings

logger = logging.getLogger(__name__)

TABLE_NAME = "langchain_chat_history"


def ensure_history_table() -> None:
    """Cria a tabela de histórico se não existir (idempotente)."""
    settings = get_settings()
    if not settings.database_url:
        logger.warning("DATABASE_URL não configurada; memória LangChain indisponível.")
        return
    with psycopg.connect(settings.database_url) as conn:
        PostgresChatMessageHistory.create_tables(conn, TABLE_NAME)


def ultima_mensagem_ai(session_id: str) -> str:
    """Última fala da IA (Sofia) na sessão — dá contexto ao classificador de
    moderação para julgar respostas curtas do lead ('sim', uma data...)."""
    settings = get_settings()
    if not settings.database_url:
        return ""
    try:
        with psycopg.connect(settings.database_url) as conn:
            row = conn.execute(
                f"select message from {TABLE_NAME} "
                "where session_id = %s and message->>'type' = 'ai' "
                "order by id desc limit 1",
                (str(session_id),),
            ).fetchone()
    except Exception:
        logger.exception("Falha ao ler última fala da IA (session=%s)", session_id)
        return ""
    if not row:
        return ""
    return str((row[0] or {}).get("data", {}).get("content", ""))[:500]


def mensagens_humanas(session_id: str) -> str:
    """Concatena todas as falas do LEAD (humano) na sessão.

    Usada para verificar, de forma determinística, se um dado que a tool vai
    gravar (ex.: URL do LinkedIn) realmente foi escrito pelo lead — barreira
    contra o agente inventar o valor para preencher um campo obrigatório.
    """
    settings = get_settings()
    if not settings.database_url:
        return ""
    try:
        with psycopg.connect(settings.database_url) as conn:
            rows = conn.execute(
                f"select message from {TABLE_NAME} "
                "where session_id = %s and message->>'type' = 'human' "
                "order by id",
                (str(session_id),),
            ).fetchall()
    except Exception:
        logger.exception("Falha ao ler mensagens humanas (session=%s)", session_id)
        return ""
    partes = [str((r[0] or {}).get("data", {}).get("content", "")) for r in rows]
    return "\n".join(p for p in partes if p)


def get_session_history(session_id: str) -> PostgresChatMessageHistory:
    """Factory usada pelo RunnableWithMessageHistory.

    Abre uma conexão dedicada por histórico; o finalizer garante o fechamento
    quando o objeto sai de escopo (fim do turno do agente).
    """
    settings = get_settings()
    conn = psycopg.connect(settings.database_url, autocommit=True)
    history = PostgresChatMessageHistory(
        TABLE_NAME,
        str(session_id),
        sync_connection=conn,
    )
    weakref.finalize(history, conn.close)
    return history
