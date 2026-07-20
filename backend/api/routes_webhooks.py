"""Webhooks de entrada (Evolution API -> backend)."""

import logging

from fastapi import APIRouter, Request

from api.schemas import WebhookAck
from services import agent_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/evolution", response_model=WebhookAck)
async def evolution_webhook(request: Request) -> WebhookAck:
    """Recebe eventos da Evolution API (mensagens de WhatsApp dos leads).

    Configurado na Evolution como webhook do evento MESSAGES_UPSERT apontando
    para http://host.docker.internal:8000/api/v1/webhooks/evolution.
    Sempre responde 200 para a Evolution não reencaminhar o evento.
    """
    try:
        payload = await request.json()
    except Exception:
        return WebhookAck(status="ignored", detail="payload não é JSON")

    incoming = whatsapp_service.parse_incoming(payload)
    if incoming is None:
        return WebhookAck(status="ignored", detail="evento irrelevante")

    try:
        resposta = agent_service.handle_incoming_message(incoming)
    except Exception:
        logger.exception("Erro ao processar mensagem de %s", incoming.phone_e164)
        return WebhookAck(status="ignored", detail="erro interno ao processar")

    if resposta is None:
        return WebhookAck(status="ignored", detail="lead/conversa não encontrados")
    return WebhookAck(status="processed")
