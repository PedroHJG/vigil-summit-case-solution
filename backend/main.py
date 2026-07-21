"""Vigil Summit — Backend FastAPI.

Executar localmente (a partir de /backend):
    uvicorn main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import routes_internal, routes_leads, routes_webhooks
from api.schemas import HealthResponse
from core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend do Vigil Summit: captação de leads, enriquecimento por scraping, "
        "agente de qualificação LangChain + Claude via WhatsApp (Evolution API), "
        "human-in-the-loop (Google Sheets), notificações e follow-up pós-evento "
        "(Google Calendar). O n8n atua apenas como roteador dos endpoints internos."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Libera também origens da rede local (celular acessando o dev server pelo
    # IP do PC, ex.: http://192.168.0.15:5173) sem precisar editar CORS_ORIGINS
    # a cada troca de IP. Restrito a faixas privadas — não afeta produção.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_leads.router)
app.include_router(routes_internal.router)
app.include_router(routes_webhooks.router)


@app.on_event("startup")
def startup() -> None:
    # Grava credenciais Google a partir de env vars, se fornecidas (deploys
    # sem filesystem versionável, ex. Render) — nunca falha o boot.
    try:
        from core.bootstrap_credentials import materialize_google_credentials

        materialize_google_credentials()
    except Exception:
        logger.warning("Falha ao materializar credenciais Google via env var.", exc_info=True)

    # Garante a tabela de memória do LangChain (idempotente); a migration 0001
    # também a cria, então falhas aqui não são fatais.
    try:
        from agent.memory import ensure_history_table

        ensure_history_table()
    except Exception:
        logger.warning(
            "Não foi possível garantir a tabela de memória do LangChain "
            "(verifique DATABASE_URL).",
            exc_info=True,
        )


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(app=settings.app_name, version=settings.app_version)
