"""Tool de RAG: consulta a base de conhecimento do evento (pgvector + Voyage).

O agente chama sob demanda quando o lead pergunta sobre o evento (agenda,
sessões, formato, FAQ) ou quando precisa personalizar uma mensagem de
antecipação/follow-up com base no conteúdo programático. Em vez de carregar
toda a base em todo turno, recupera apenas os trechos relevantes.
"""

import json
import logging

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from services import knowledge_service

logger = logging.getLogger(__name__)


class ConsultarConteudoArgs(BaseModel):
    pergunta: str = Field(
        description=(
            "Pergunta ou tema em linguagem natural para buscar na base de "
            "conhecimento do evento (ex.: 'sessão sobre compliance', 'horário "
            "do almoço', 'posso levar acompanhante')."
        )
    )


def consultar_conteudo_evento(pergunta: str) -> str:
    """Busca semântica na base de conhecimento; retorna os trechos relevantes."""
    try:
        resultados = knowledge_service.search(pergunta)
    except RuntimeError:
        # VOYAGE_API_KEY ausente — RAG indisponível, mas o turno não pode cair.
        return json.dumps(
            {"erro": "Base de conhecimento indisponível no momento; responda com os "
                     "dados gerais do evento que você já tem."},
            ensure_ascii=False,
        )
    except Exception as exc:
        # Rate limit da Voyage (3 RPM no free tier sem cartão) ou rede.
        logger.warning("Falha ao consultar base de conhecimento: %s", exc)
        return json.dumps(
            {"erro": "Não consegui consultar os detalhes agora; use os dados gerais do "
                     "evento e ofereça verificar o detalhe específico em seguida."},
            ensure_ascii=False,
        )

    if not resultados:
        return json.dumps(
            {"resultado": "Nenhum trecho relevante encontrado na base do evento."},
            ensure_ascii=False,
        )

    trechos = [
        {"secao": r["heading"], "conteudo": r["content"]}
        for r in resultados
    ]
    return json.dumps({"trechos": trechos}, ensure_ascii=False)


def make_conteudo_evento_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=consultar_conteudo_evento,
        name="consultar_conteudo_evento",
        description=(
            "Consulta a base de conhecimento oficial do Vigil Summit (agenda, "
            "sessões e temas, formato do dia, FAQ, público-alvo). Use SEMPRE que o "
            "lead perguntar detalhes sobre o evento, ou quando você precisar "
            "personalizar uma mensagem citando uma sessão específica de acordo com "
            "o perfil/dor do lead. Não invente detalhes do programa — consulte aqui."
        ),
        args_schema=ConsultarConteudoArgs,
    )