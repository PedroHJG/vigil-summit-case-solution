"""Integração com a Evolution API (envio e parsing de mensagens de WhatsApp)."""

import json
import logging
import re

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from api.schemas import IncomingMessage
from core.config import get_settings

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    # Rate limit / instabilidade da Evolution API
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in (429, 500, 502, 503, 504)
    )


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def send_text(phone_e164: str, text: str) -> dict:
    """Envia mensagem de texto via POST /message/sendText/{instance}."""
    settings = get_settings()
    number = re.sub(r"\D", "", phone_e164)

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}",
            headers={"apikey": settings.evolution_api_key},
            json={"number": number, "text": text},
        )
        resp.raise_for_status()
        return resp.json()


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def _post(path: str, body: dict) -> dict:
    settings = get_settings()
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{settings.evolution_api_url}{path}/{settings.evolution_instance}",
            headers={"apikey": settings.evolution_api_key},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()


def send_confirmation_prompt(phone_e164: str, title: str, description: str,
                             confirm_id: str, confirm_label: str,
                             decline_id: str, decline_label: str) -> str:
    """Envia a mensagem interativa de confirmação (botões).

    Fallbacks: sendButtons -> sendList -> texto simples. Alguns canais do
    WhatsApp rejeitam botões; a lista cobre esses casos e o texto é a rede
    final de segurança. Retorna qual formato foi efetivamente enviado.
    """
    number = re.sub(r"\D", "", phone_e164)

    try:
        _post("/message/sendButtons", {
            "number": number,
            "title": title,
            "description": description,
            "footer": "Vigil Summit",
            "buttons": [
                {"type": "reply", "displayText": confirm_label, "id": confirm_id},
                {"type": "reply", "displayText": decline_label, "id": decline_id},
            ],
        })
        return "buttons"
    except httpx.HTTPError as exc:
        logger.warning("sendButtons falhou (%s); tentando sendList.", exc)

    try:
        _post("/message/sendList", {
            "number": number,
            "title": title,
            "description": description,
            "buttonText": "Responder",
            "footerText": "Vigil Summit",
            "sections": [{
                "title": "Sua inscrição",
                "rows": [
                    {"title": confirm_label, "rowId": confirm_id},
                    {"title": decline_label, "rowId": decline_id},
                ],
            }],
        })
        return "list"
    except httpx.HTTPError as exc:
        logger.warning("sendList falhou (%s); enviando texto simples.", exc)

    send_text(
        phone_e164,
        f"{title}\n\n{description}\n\nResponda *SIM* para confirmar ou *NÃO* caso não possa ir.",
    )
    return "text"


def parse_incoming(payload: dict) -> IncomingMessage | None:
    """Normaliza o webhook messages.upsert da Evolution API v2.

    Cobre texto simples e respostas de mensagens interativas (botões/lista).
    Retorna None para eventos irrelevantes (mensagens enviadas por nós,
    grupos, eventos de conexão, mensagens sem conteúdo).
    """
    event = str(payload.get("event", "")).lower().replace("_", ".")
    if event != "messages.upsert":
        return None

    data = payload.get("data") or {}
    key = data.get("key") or {}

    if key.get("fromMe"):
        return None

    remote_jid = str(key.get("remoteJid", ""))
    if not remote_jid.endswith("@s.whatsapp.net"):
        return None  # ignora grupos (@g.us) e broadcasts

    message = data.get("message") or {}

    text = ""
    button_id = None

    # Resposta de botão (formatos usados pela Evolution/Baileys). O sendButtons
    # atual gera interactiveMessage/nativeFlow, cuja resposta chega como
    # interactiveResponseMessage com o id dentro de paramsJson.
    btn = message.get("buttonsResponseMessage") or {}
    tpl = message.get("templateButtonReplyMessage") or {}
    lst = message.get("listResponseMessage") or {}
    itv = message.get("interactiveResponseMessage") or {}
    if btn:
        button_id = btn.get("selectedButtonId")
        text = btn.get("selectedDisplayText") or ""
    elif tpl:
        button_id = tpl.get("selectedId")
        text = tpl.get("selectedDisplayText") or ""
    elif lst:
        button_id = (lst.get("singleSelectReply") or {}).get("selectedRowId")
        text = lst.get("title") or ""
    elif itv:
        params_raw = (itv.get("nativeFlowResponseMessage") or {}).get("paramsJson") or "{}"
        try:
            params = json.loads(params_raw)
        except json.JSONDecodeError:
            params = {}
        button_id = params.get("id")
        text = params.get("display_text") or (itv.get("body") or {}).get("text") or ""
    else:
        text = (
            message.get("conversation")
            or (message.get("extendedTextMessage") or {}).get("text")
            or ""
        )

    text = str(text).strip()
    if not text and not button_id:
        return None

    phone = "+" + re.sub(r"\D", "", remote_jid.split("@")[0])
    return IncomingMessage(
        phone_e164=phone,
        text=text or "(resposta interativa)",
        message_id=key.get("id"),
        push_name=data.get("pushName"),
        button_id=button_id,
    )
