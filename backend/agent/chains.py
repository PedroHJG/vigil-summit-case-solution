"""Definição dos fluxos LangChain (pré-evento, pós-evento e enriquecimento).

- Chain de enriquecimento: pipeline determinístico prompt | Claude | JSON.
- Agentes conversacionais: create_tool_calling_agent + AgentExecutor, com
  memória nativa via RunnableWithMessageHistory + PostgresChatMessageHistory.
"""

import logging
from datetime import datetime

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

from agent.memory import get_session_history
from agent.prompts import (
    ENRICHMENT_SUMMARY_HUMAN,
    ENRICHMENT_SUMMARY_SYSTEM,
    POST_EVENT_SYSTEM_PROMPT,
    PRE_EVENT_SYSTEM_PROMPT,
)
from agent.tools.calendar import make_calendar_tool, make_disponibilidade_tool
from agent.tools.confirmation import (
    make_confirmar_inscricao_tool,
    make_enviar_botao_confirmacao_tool,
)
from agent.tools.crm import make_acompanhantes_tool, make_crm_tool
from agent.tools.sheets import make_registrar_curadoria_tool, make_sheets_tool
from core.config import get_settings

logger = logging.getLogger(__name__)

MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _event_date_humana(dt: datetime) -> str:
    return f"{dt.day} de {MESES_PT[dt.month - 1]} de {dt.year}, às {dt.strftime('%Hh%M')}"


def build_llm() -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=settings.anthropic_max_tokens,
        timeout=120,
        max_retries=3,  # o SDK aplica backoff exponencial em 429/5xx
    )


# =============================================================================
# Chain de enriquecimento (scraping -> resumo estruturado)
# =============================================================================

def build_enrichment_summary_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ENRICHMENT_SUMMARY_SYSTEM),
            ("human", ENRICHMENT_SUMMARY_HUMAN),
        ]
    )
    return prompt | build_llm() | JsonOutputParser()


# =============================================================================
# Agentes conversacionais (WhatsApp) com memória nativa do LangChain
# =============================================================================

def _lead_prompt_vars(lead: dict, contexto_empresa: str) -> dict:
    settings = get_settings()
    return {
        "event_name": settings.event_name,
        "event_date_humana": _event_date_humana(settings.event_date),
        "event_location": settings.event_location,
        "nome_lead": lead["nome"],
        "cargo": lead.get("cargo_validado") or lead["cargo"],
        "empresa": lead["empresa"],
        "contexto_empresa": contexto_empresa or "(sem contexto adicional disponível)",
    }


def _build_conversational_agent(system_text: str, tools: list) -> RunnableWithMessageHistory:
    # O system prompt já vem formatado; usar SystemMessage evita que chaves `{}`
    # do conteúdo sejam interpretadas como variáveis do template.
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_text),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(build_llm(), tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=6,
        handle_parsing_errors=True,
        verbose=False,
    )
    # O Claude pode devolver o output final como lista de blocos de conteúdo;
    # o RunnableWithMessageHistory só sabe persistir string/BaseMessage — sem
    # esta normalização o callback de gravação quebra e o histórico se perde.
    pipeline = executor | RunnableLambda(
        lambda result: {"output": _content_to_text(result.get("output", ""))}
    )
    return RunnableWithMessageHistory(
        pipeline,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="output",
    )


def build_pre_event_chain(lead: dict, contexto_empresa: str) -> RunnableWithMessageHistory:
    """Agente de engajamento/qualificação pré-evento."""
    system_text = PRE_EVENT_SYSTEM_PROMPT.format(**_lead_prompt_vars(lead, contexto_empresa))
    tools = [
        make_registrar_curadoria_tool(lead),
        make_sheets_tool(lead),
        make_enviar_botao_confirmacao_tool(lead),
        make_confirmar_inscricao_tool(lead),
        make_acompanhantes_tool(lead["id"]),
        make_crm_tool(lead["id"]),
    ]
    return _build_conversational_agent(system_text, tools)


def build_post_event_chain(lead: dict, contexto_empresa: str) -> RunnableWithMessageHistory:
    """Agente de follow-up comercial pós-evento (agendamento de reunião)."""
    system_text = POST_EVENT_SYSTEM_PROMPT.format(**_lead_prompt_vars(lead, contexto_empresa))
    tools = [
        make_disponibilidade_tool(),
        make_calendar_tool(lead),
        make_crm_tool(lead["id"]),
    ]
    return _build_conversational_agent(system_text, tools)


def _content_to_text(output) -> str:
    """Converte o output do agente (string ou blocos de conteúdo) em texto puro."""
    if isinstance(output, list):
        parts = []
        for block in output:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p).strip()
    return str(output).strip()


def extract_output_text(result: dict) -> str:
    """Extrai o texto final de uma invocação do agente."""
    return _content_to_text(result.get("output", ""))
