"""Tools de confirmação de inscrição (usadas pelo agente pré-evento)."""

import json
import logging

from langchain_core.tools import StructuredTool

from core.config import get_settings

logger = logging.getLogger(__name__)

# IDs das opções da mensagem interativa (o webhook os devolve em button_id)
CONFIRM_BUTTON_ID = "confirmar_inscricao"
DECLINE_BUTTON_ID = "recusar_inscricao"

# Sentinela: quando o agente responde exatamente isso, nada é enviado ao lead
# (usada quando uma tool já entregou a mensagem interativa).
NO_REPLY_SENTINEL = "[FIM]"


def make_enviar_botao_confirmacao_tool(lead: dict) -> StructuredTool:
    """Tool que envia a mensagem interativa (botões) de confirmação."""

    def _enviar() -> str:
        from services import whatsapp_service

        settings = get_settings()
        data_str = settings.event_date.strftime("%d/%m/%Y às %H:%M")
        try:
            formato = whatsapp_service.send_confirmation_prompt(
                lead["telefone_e164"],
                title=f"🎟️ {settings.event_name}",
                description=(
                    f"{lead['nome'].split()[0]}, sua vaga foi aprovada pela curadoria! "
                    f"O evento acontece em {data_str} — {settings.event_location}. "
                    "Confirma sua inscrição?"
                ),
                confirm_id=CONFIRM_BUTTON_ID,
                confirm_label="✅ Confirmar inscrição",
                decline_id=DECLINE_BUTTON_ID,
                decline_label="Não poderei ir",
            )
        except Exception as exc:
            logger.warning("Falha ao enviar botão de confirmação: %s", exc)
            return json.dumps(
                {"erro": "Não foi possível enviar a mensagem interativa agora."},
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "status": "enviada",
                "formato": formato,
                "instrucao": (
                    "A mensagem interativa foi aceita pela API, mas o WhatsApp nem sempre a "
                    "exibe. Envie AGORA um texto curto complementar pedindo que ele responda "
                    "por escrito (ex.: 'se os botões não aparecerem, é só responder SIM')."
                ),
            },
            ensure_ascii=False,
        )

    return StructuredTool.from_function(
        func=_enviar,
        name="enviar_botao_confirmacao",
        description=(
            "Envia ao lead a mensagem interativa do WhatsApp (botões) para ele "
            "confirmar a inscrição no evento. Use quando o lead demonstrar "
            "intenção de participar. Não recebe argumentos."
        ),
    )


def make_confirmar_inscricao_tool(lead: dict) -> StructuredTool:
    """Tool que efetiva a confirmação quando o lead confirma por texto."""

    def _confirmar() -> str:
        from core.config import get_settings
        from services import confirmation_service, lead_service

        lead_atual = lead_service.get_lead(lead["id"])
        resultado = confirmation_service.confirm_lead(lead_atual)

        if resultado.get("esgotado"):
            s = get_settings()
            return json.dumps(
                {
                    "status": "esgotado",
                    "detalhe": (
                        f"As {s.event_capacity} vagas do evento já se esgotaram — NÃO foi "
                        "possível confirmar. Avise o lead com empatia que ele entrou na "
                        "lista de espera e será avisado se abrir vaga."
                    ),
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "status": "confirmado",
                "ja_estava_confirmado": resultado["ja_confirmado"],
                "detalhe": (
                    "Inscrição confirmada: e-mail de confirmação enviado e lembretes "
                    "do evento agendados."
                ),
                "proxima_acao": (
                    "Envie AGORA a mensagem de feedback ao lead: comemore a confirmação, "
                    "repita data e local do evento, avise do e-mail de confirmação e "
                    "pergunte se ele quer levar até 2 acompanhantes do time (assentos "
                    "reservados pela curadoria)."
                ),
            },
            ensure_ascii=False,
        )

    return StructuredTool.from_function(
        func=_confirmar,
        name="confirmar_inscricao",
        description=(
            "Efetiva a confirmação da inscrição do lead no evento (status, convite "
            "no Google Calendar, e-mail de confirmação e lembretes). Use quando o "
            "lead confirmar por TEXTO (ex.: 'sim, confirmo') em vez do botão. "
            "Não recebe argumentos."
        ),
    )