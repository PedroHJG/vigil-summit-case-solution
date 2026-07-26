"""Orquestra os agentes LangChain: início de conversa, turnos e follow-up.

Toda invocação do agente passa por aqui; o histórico é carregado/persistido
automaticamente pelo RunnableWithMessageHistory (memória nativa do LangChain).
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from agent.chains import (
    build_post_event_chain,
    build_pre_event_chain,
    extract_output_text,
)
from agent.prompts import (
    KICKOFF_BUTTON_CONFIRMED,
    KICKOFF_BUTTON_DECLINED,
    KICKOFF_POST_EVENT,
    KICKOFF_PRE_EVENT,
    KICKOFF_REENGAGE,
    KICKOFF_REENGAGE_ASK_CARGO,
)
from agent.tools.confirmation import (
    CONFIRM_BUTTON_ID,
    DECLINE_BUTTON_ID,
    NO_REPLY_SENTINEL,
)
from api.schemas import EngageResult, FollowUpRunResult, IncomingMessage
from core.config import get_settings
from core.supabase_client import get_supabase
from services import enrichment_service, lead_service, notification_service, whatsapp_service

logger = logging.getLogger(__name__)

# Rede de segurança: se QUALQUER tool ou chamada ao LLM falhar de forma
# inesperada (credencial expirada, API fora do ar etc.), o lead recebe isto
# em vez de silêncio absoluto — nunca deixamos uma mensagem sem resposta.
FALLBACK_ERROR_MESSAGE = (
    "Desculpa, tive um probleminha técnico agora e não consegui processar sua "
    "mensagem 🙏 Já estou verificando — pode repetir em alguns minutos ou "
    "nosso time entra em contato em breve."
)

# Enviada quando o evento está lotado e o lead ainda não tem vaga garantida.
SOLD_OUT_MESSAGE = (
    "Poxa, tenho uma notícia difícil 😕 As vagas do {event_name} se esgotaram — "
    "são apenas {capacity} lugares e todos já foram confirmados. Coloquei você na "
    "lista de espera e, se abrir uma vaga, aviso você imediatamente por aqui. "
    "Obrigada pelo interesse!"
)

# Enviada UMA vez, quando o lead atinge o limite de mensagens fora de contexto.
BLOQUEIO_MESSAGE = (
    "Percebi que nossas últimas mensagens fugiram bastante do tema do {event_name} 😅 "
    "Sou uma assistente dedicada só ao evento, então vou pausar nosso atendimento por "
    "{horas}h. Depois disso, é só me chamar que retomo tudo sobre a sua inscrição. Até já!"
)


# =============================================================================
# Conversas
# =============================================================================

def _get_or_create_conversation(lead_id: str, fase: str) -> dict:
    supabase = get_supabase()
    result = (
        supabase.table("conversations")
        .select("*")
        .eq("lead_id", lead_id)
        .eq("fase", fase)
        .execute()
    )
    if result.data:
        return result.data[0]
    created = (
        supabase.table("conversations")
        .insert({"lead_id": lead_id, "fase": fase})
        .execute()
    )
    return created.data[0]


def _active_conversation(lead_id: str) -> dict | None:
    """Conversa ativa do lead; pós-evento tem prioridade sobre pré-evento."""
    supabase = get_supabase()
    result = (
        supabase.table("conversations")
        .select("*")
        .eq("lead_id", lead_id)
        .eq("status", "ativa")
        .execute()
    )
    if not result.data:
        return None
    convs = sorted(result.data, key=lambda c: c["fase"] != "pos_evento")
    return convs[0]


def _build_chain(lead: dict, fase: str, texto_do_lead: str = ""):
    contexto = enrichment_service.get_enrichment_context(lead["id"])
    if fase == "pos_evento":
        return build_post_event_chain(lead, contexto)
    return build_pre_event_chain(lead, contexto, texto_do_lead)


def _invoke(lead: dict, fase: str, session_id: str, user_input: str) -> str:
    # Reúne tudo que o lead escreveu (histórico + mensagem atual) para a tool de
    # curadoria validar a procedência do LinkedIn (anti-alucinação).
    from agent.memory import mensagens_humanas

    texto_do_lead = ""
    if fase == "pre_evento" and not user_input.startswith("[INSTRUÇÃO INTERNA]"):
        texto_do_lead = f"{mensagens_humanas(session_id)}\n{user_input}".strip()

    chain = _build_chain(lead, fase, texto_do_lead)
    result = chain.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": str(session_id)}},
    )
    text = extract_output_text(result)
    if not text:
        raise RuntimeError("Agente retornou resposta vazia.")
    return text


# =============================================================================
# Fluxos
# =============================================================================

def start_pre_event(lead_id: str) -> EngageResult:
    """Primeira mensagem de qualificação (chamado pelo n8n após o enriquecimento)."""
    lead = lead_service.get_lead(lead_id)
    conversation = _get_or_create_conversation(lead_id, "pre_evento")

    mensagem = _invoke(lead, "pre_evento", conversation["session_id"], KICKOFF_PRE_EVENT)
    whatsapp_service.send_text(lead["telefone_e164"], mensagem)

    lead_service.update_status(lead_id, "em_conversa", "Agente iniciou a qualificação")
    lead_service.log_event(lead_id, "engajamento_iniciado", {"fase": "pre_evento"})

    return EngageResult(
        lead_id=lead_id,
        conversation_id=conversation["id"],
        session_id=conversation["session_id"],
        mensagem_inicial=mensagem,
    )


def handle_incoming_message(incoming: IncomingMessage) -> str | None:
    """Processa uma mensagem (texto ou clique de botão) recebida no WhatsApp."""
    phone_e164 = incoming.phone_e164
    lead = lead_service.get_lead_by_phone(phone_e164)
    if not lead:
        logger.info("Mensagem de número desconhecido: %s", phone_e164)
        return None

    conversation = _active_conversation(lead["id"])
    if not conversation:
        logger.info("Lead %s sem conversa ativa; mensagem ignorada.", lead["id"])
        return None

    # Bloqueio por abuso de contexto: se ativo, ignora em SILÊNCIO (sem LLM, sem
    # envio) — economia máxima. Se já expirou, limpa e volta a atender.
    if lead_service.bloqueio_ativo(lead):
        logger.info("Lead %s bloqueado (off-topic); mensagem ignorada.", lead["id"])
        return None
    if lead.get("bloqueado_ate"):  # existia mas expirou
        lead_service.limpar_bloqueio(lead["id"])

    # Evento lotado: se o lead ainda NÃO tem vaga garantida, qualquer interação
    # recebe o aviso de esgotado (curto-circuito, sem gastar turno do agente).
    # Quem já está confirmado/pós-evento segue o fluxo normal.
    if not lead_service.tem_vaga_garantida(lead) and lead_service.evento_lotado():
        settings = get_settings()
        msg = SOLD_OUT_MESSAGE.format(
            event_name=settings.event_name, capacity=settings.event_capacity
        )
        try:
            whatsapp_service.send_text(phone_e164, msg)
        except Exception:
            logger.exception("Falha ao enviar aviso de esgotado ao lead %s", lead["id"])
        lead_service.log_event(lead["id"], "interacao_evento_lotado", {})
        return msg

    # Qualquer resposta do lead marca o último toque da régua como respondido
    # (alimenta a lógica de "mudar o ângulo" do próximo toque).
    try:
        from services import cadence_service

        cadence_service.mark_last_touch_responded(lead["id"])
    except Exception:
        logger.exception("Falha ao marcar toque da régua como respondido")

    # Cliques na mensagem interativa de confirmação: efeito determinístico no
    # backend + turno do agente via instrução interna (memória fica consistente).
    if incoming.button_id == CONFIRM_BUTTON_ID:
        from services import confirmation_service

        resultado = confirmation_service.confirm_lead(lead)
        # Corrida rara: encheu entre o envio do botão e o clique.
        if resultado.get("esgotado"):
            settings = get_settings()
            msg = SOLD_OUT_MESSAGE.format(
                event_name=settings.event_name, capacity=settings.event_capacity
            )
            whatsapp_service.send_text(phone_e164, msg)
            return msg
        agent_input = KICKOFF_BUTTON_CONFIRMED
    elif incoming.button_id == DECLINE_BUTTON_ID:
        agent_input = KICKOFF_BUTTON_DECLINED
    else:
        # Moderação de contexto: um classificador LEVE (Haiku) decide se a
        # mensagem é sobre o evento antes de acionar o agente caro (Opus + tools).
        # Off-topic é redirecionado sem tocar no Opus; após N consecutivas, bloqueia.
        resultado_mod = _moderar_contexto(lead, conversation, incoming.text)
        if resultado_mod is not None:
            return resultado_mod  # já respondeu (redirecionamento ou bloqueio)
        agent_input = incoming.text

    status_antes = lead["status"]
    try:
        resposta = _invoke(lead, conversation["fase"], conversation["session_id"], agent_input)
    except Exception:
        # Nunca deixar o lead sem resposta: uma tool (ex.: Google Calendar com
        # credencial expirada) pode falhar de formas que o prompt não previu.
        logger.exception(
            "Falha ao gerar resposta do agente para o lead %s (fase=%s)",
            lead["id"], conversation["fase"],
        )
        whatsapp_service.send_text(phone_e164, FALLBACK_ERROR_MESSAGE)
        lead_service.log_event(
            lead["id"], "erro_turno_agente", {"fase": conversation["fase"]}
        )
        return FALLBACK_ERROR_MESSAGE

    if resposta.strip() == NO_REPLY_SENTINEL:
        # Uma tool já entregou a mensagem interativa neste turno.
        return resposta

    try:
        whatsapp_service.send_text(phone_e164, resposta)
    except Exception:
        logger.exception("Falha ao enviar resposta ao lead %s via WhatsApp", lead["id"])
        return None

    # Se o agente qualificou o lead neste turno, alerta o time comercial.
    lead_depois = lead_service.get_lead(lead["id"])
    if lead_depois["status"] == "qualificado" and status_antes != "qualificado":
        notification_service.schedule_internal_alert(
            lead_depois, "Lead qualificado pelo agente na conversa de WhatsApp"
        )

    return resposta


def _moderar_contexto(lead: dict, conversation: dict, texto: str) -> str | None:
    """Filtra mensagens fora do tema (economiza tokens e mantém o contexto).

    Retorna:
    - None  -> mensagem no contexto; siga para o agente Opus.
    - str   -> já respondeu ao lead (redirecionamento leve ou aviso de bloqueio);
               o agente caro NÃO é acionado.
    """
    from agent.memory import ultima_mensagem_ai
    from services import moderation_service

    settings = get_settings()
    ultima_sofia = ultima_mensagem_ai(conversation["session_id"])
    veredito = moderation_service.classify(texto, ultima_sofia)

    if not veredito["fora_de_contexto"]:
        # Voltou ao contexto: zera a sequência de off-topic.
        if lead.get("off_topic_streak"):
            lead_service.resetar_offtopic(lead["id"])
        return None

    streak = lead_service.registrar_offtopic(lead["id"])

    # Atingiu o limite -> bloqueia por N horas e avisa (uma única vez).
    if streak >= settings.offtopic_block_threshold:
        lead_service.bloquear_lead(lead["id"], settings.offtopic_block_hours)
        msg = BLOQUEIO_MESSAGE.format(
            event_name=settings.event_name, horas=settings.offtopic_block_hours
        )
        try:
            whatsapp_service.send_text(lead["telefone_e164"], msg)
        except Exception:
            logger.exception("Falha ao enviar aviso de bloqueio ao lead %s", lead["id"])
        return msg

    # Abaixo do limite: redireciona com uma resposta LEVE (do classificador Haiku),
    # sem acionar o Opus. Fallback fixo caso o classificador não gere a frase.
    redirect = veredito["redirecionamento"] or (
        "Consigo te ajudar só com assuntos do Vigil Summit 😊 Voltando pra lá: "
        "quer que eu siga com a sua inscrição?"
    )
    try:
        whatsapp_service.send_text(lead["telefone_e164"], redirect)
    except Exception:
        logger.exception("Falha ao enviar redirecionamento ao lead %s", lead["id"])
    lead_service.log_event(lead["id"], "mensagem_offtopic", {"streak": streak})
    return redirect


def send_proactive_touch(lead: dict, kickoff: str) -> str:
    """Envia um toque da régua proativa na conversa pré-evento do lead."""
    conversation = _get_or_create_conversation(lead["id"], "pre_evento")
    mensagem = _invoke(lead, "pre_evento", conversation["session_id"], kickoff)
    if mensagem.strip() != NO_REPLY_SENTINEL:
        whatsapp_service.send_text(lead["telefone_e164"], mensagem)
    return mensagem


def reengage_after_validation(lead_id: str, perguntar_cargo: bool) -> str:
    """Retoma a conversa quando a curadoria humana aprova o lead (FASE 2)."""
    lead = lead_service.get_lead(lead_id)
    conversation = _get_or_create_conversation(lead_id, "pre_evento")

    kickoff = KICKOFF_REENGAGE_ASK_CARGO if perguntar_cargo else KICKOFF_REENGAGE
    mensagem = _invoke(lead, "pre_evento", conversation["session_id"], kickoff)
    if mensagem.strip() != NO_REPLY_SENTINEL:
        whatsapp_service.send_text(lead["telefone_e164"], mensagem)

    notification_service.schedule_internal_alert(
        lead, "Lead aprovado pela curadoria; agente reengajou para confirmação"
    )
    lead_service.log_event(
        lead_id, "reengajamento_pos_validacao", {"perguntar_cargo": perguntar_cargo}
    )
    return mensagem


def start_follow_up(lead_id: str) -> str:
    """Retoma o contato pós-evento (agendamento de reunião comercial)."""
    lead = lead_service.get_lead(lead_id)
    if lead["status"] not in ("compareceu", "em_follow_up"):
        raise HTTPException(
            status_code=409,
            detail=f"Follow-up requer status 'compareceu' (atual: {lead['status']}).",
        )

    # Encerra a conversa pré-evento para o roteamento de mensagens priorizar a nova fase
    supabase = get_supabase()
    supabase.table("conversations").update({"status": "encerrada"}).eq(
        "lead_id", lead_id
    ).eq("fase", "pre_evento").execute()

    conversation = _get_or_create_conversation(lead_id, "pos_evento")
    mensagem = _invoke(lead, "pos_evento", conversation["session_id"], KICKOFF_POST_EVENT)
    whatsapp_service.send_text(lead["telefone_e164"], mensagem)

    lead_service.update_status(lead_id, "em_follow_up", "Follow-up pós-evento iniciado")
    lead_service.log_event(lead_id, "follow_up_iniciado", {"fase": "pos_evento"})
    return mensagem


def run_follow_ups() -> FollowUpRunResult:
    """Dispara follow-up para todos os participantes (chamado pelo n8n após o evento)."""
    settings = get_settings()
    if datetime.now(timezone.utc) < settings.event_date.astimezone(timezone.utc):
        return FollowUpRunResult(
            leads_processados=[], detalhes=["Evento ainda não ocorreu; nada a fazer."]
        )

    processados: list = []
    detalhes: list[str] = []
    for lead in lead_service.list_leads_by_status("compareceu"):
        try:
            start_follow_up(lead["id"])
            processados.append(lead["id"])
        except Exception as exc:
            logger.exception("Falha no follow-up do lead %s", lead["id"])
            detalhes.append(f"{lead['id']}: {exc}")

    return FollowUpRunResult(leads_processados=processados, detalhes=detalhes)
