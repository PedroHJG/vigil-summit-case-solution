"""Moderação de contexto: filtra mensagens fora do tema do evento.

Um classificador LEVE (Haiku) roda ANTES do agente principal (Opus + tools +
RAG). Objetivo duplo:
1. Evitar que o agente "morda a isca" e responda perguntas off-topic (fugir do
   contexto do evento).
2. Economizar tokens: uma chamada Haiku barata decide se vale acionar o agente
   caro; mensagens off-topic são respondidas por um redirecionamento gerado na
   MESMA chamada, sem tocar no Opus.

Após N mensagens off-topic consecutivas (config), o lead é bloqueado por
algumas horas — aí nem o Haiku roda.
"""

import json
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.config import get_settings

logger = logging.getLogger(__name__)

_CLASSIFIER_SYSTEM = """Você é um filtro de contexto para a Sofia, SDR virtual do evento \
"{event_name}" (segurança cibernética e IA). A Sofia conversa por WhatsApp com um lead para \
qualificá-lo, confirmar inscrição, tratar acompanhantes/logística e, no pós-evento, agendar \
reunião comercial.

Classifique a MENSAGEM DO LEAD abaixo. É "no contexto" se tem qualquer relação com: o evento \
(agenda, sessões, local, data, formato, acompanhantes), a inscrição/confirmação, a empresa/cargo \
do lead, segurança/tecnologia/IA, agendamento de reunião, ou é uma resposta natural à última \
fala da Sofia (ex.: "sim", "pode ser", uma data, um número, "não tenho certeza", uma saudação, \
uma despedida, pedir para parar de receber mensagens).

É "fora de contexto" se o lead usa a Sofia como assistente genérico ou tenta desviá-la do \
propósito: pedir poema/receita/piada, perguntas de conhecimentos gerais, código, temas sem \
qualquer ligação com o evento/segurança, provocações ou spam.

Responda EXCLUSIVAMENTE com um JSON válido (sem markdown) com as chaves:
- "fora_de_contexto": booleano.
- "redirecionamento": se fora_de_contexto=true, uma frase curta, gentil e humana (estilo \
WhatsApp, no máximo 1 emoji) que NÃO responde ao pedido off-topic e traz o lead de volta ao \
evento. Se fora_de_contexto=false, use string vazia."""

_CLASSIFIER_HUMAN = """Última fala da Sofia (contexto): {ultima_sofia}

MENSAGEM DO LEAD: {mensagem}"""


def _classifier_chain():
    settings = get_settings()
    llm = ChatAnthropic(
        model=settings.moderation_model,
        api_key=settings.anthropic_api_key,
        max_tokens=256,
        timeout=30,
        max_retries=2,
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", _CLASSIFIER_SYSTEM), ("human", _CLASSIFIER_HUMAN)]
    )
    return prompt | llm | JsonOutputParser()


def classify(mensagem: str, ultima_sofia: str = "") -> dict:
    """Classifica a mensagem do lead. Retorna {fora_de_contexto, redirecionamento}.

    Em caso de falha do classificador, assume 'no contexto' (fail-open): é
    melhor deixar o agente responder do que bloquear um lead legítimo por um
    erro transitório.
    """
    settings = get_settings()
    try:
        result = _classifier_chain().invoke(
            {
                "event_name": settings.event_name,
                "ultima_sofia": ultima_sofia or "(início da conversa)",
                "mensagem": mensagem,
            }
        )
        return {
            "fora_de_contexto": bool(result.get("fora_de_contexto", False)),
            "redirecionamento": str(result.get("redirecionamento", "")).strip(),
        }
    except Exception:
        logger.exception("Classificador de contexto falhou; assumindo no-contexto.")
        return {"fora_de_contexto": False, "redirecionamento": ""}