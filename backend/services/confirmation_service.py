"""Confirmação efetiva da inscrição (anti no-show).

Disparada quando o lead clica no botão de confirmação do WhatsApp (ou confirma
por texto). Efeitos, em ordem:
1. status -> 'confirmado'
2. e-mail de confirmação + régua de lembretes D-7 / D-1 / H-2 agendada

Nenhum evento é criado em agenda aqui: o Google Calendar só é usado no
agendamento da reunião comercial pós-evento (agent/tools/calendar.py).
Idempotente: reconfirmar não duplica nada.
"""

import logging

from services import lead_service, notification_service

logger = logging.getLogger(__name__)


def confirm_lead(lead: dict) -> dict:
    if lead["status"] == "confirmado":
        return {"ja_confirmado": True}

    lead_service.update_status(
        lead["id"], "confirmado", "Lead confirmou inscrição pelo WhatsApp"
    )
    notification_service.schedule_confirmed_flow(lead)
    lead_service.log_event(lead["id"], "inscricao_confirmada", {})

    return {"ja_confirmado": False}