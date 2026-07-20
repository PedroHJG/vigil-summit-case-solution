"""Régua de notificações (e-mails de lembrete e alertas internos).

O n8n dispara POST /internal/notifications/run em cron; toda a decisão de
o-que-enviar-quando fica aqui (n8n é só roteador).
"""

import logging
from datetime import datetime, timedelta, timezone

from api.schemas import NotificationsRunResult
from core.config import get_settings
from core.supabase_client import get_supabase
from services import email_service

logger = logging.getLogger(__name__)


def _upsert_notifications(lead: dict, régua: list[tuple[str, datetime]]) -> None:
    """Idempotente via unique (lead_id, tipo) do banco."""
    rows = [
        {
            "lead_id": lead["id"],
            "tipo": tipo,
            "canal": "email",
            "destinatario": lead["email"],
            "scheduled_for": momento.isoformat(),
        }
        for tipo, momento in régua
    ]
    get_supabase().table("notifications").upsert(
        rows, on_conflict="lead_id,tipo", ignore_duplicates=True
    ).execute()


def schedule_for_lead(lead: dict) -> None:
    """Na captação: apenas o recibo ('recebemos sua solicitação').

    Os lembretes anti no-show só são agendados quando o lead CONFIRMA a
    inscrição (schedule_confirmed_flow) — quem não confirmou recebe régua de
    engajamento pelo WhatsApp, não spam de lembrete.
    """
    _upsert_notifications(lead, [("confirmacao_inscricao", datetime.now(timezone.utc))])


def schedule_confirmed_flow(lead: dict) -> None:
    """Na confirmação: e-mail de inscrição confirmada + lembretes D-7/D-1/H-2."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    régua = [("inscricao_confirmada", now)]
    for tipo, delta in [
        ("lembrete_d7", timedelta(days=7)),
        ("lembrete_d1", timedelta(days=1)),
        ("lembrete_h2", timedelta(hours=2)),
    ]:
        momento = settings.event_date - delta
        if momento > now:
            régua.append((tipo, momento))

    _upsert_notifications(lead, régua)


def schedule_internal_alert(lead: dict, motivo: str) -> None:
    """Alerta imediato ao time comercial (ex.: lead qualificado)."""
    settings = get_settings()
    if not settings.sales_alert_email:
        return
    get_supabase().table("notifications").upsert(
        {
            "lead_id": lead["id"],
            "tipo": "alerta_interno",
            "canal": "email",
            "destinatario": settings.sales_alert_email,
            "scheduled_for": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="lead_id,tipo",
        ignore_duplicates=True,
    ).execute()
    logger.info("Alerta interno agendado para lead %s (%s)", lead["id"], motivo)


def run_due(limit: int = 50) -> NotificationsRunResult:
    """Envia todas as notificações vencidas (scheduled_for <= agora)."""
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    due = (
        supabase.table("notifications")
        .select("*, leads(*)")
        .eq("status", "agendada")
        .lte("scheduled_for", now)
        .limit(limit)
        .execute()
    )

    enviadas = falhas = 0
    for notif in due.data or []:
        lead = notif.get("leads")
        try:
            if notif["tipo"] == "confirmacao_inscricao":
                subject, html = email_service.build_confirmation(lead)
            elif notif["tipo"] == "inscricao_confirmada":
                subject, html = email_service.build_inscricao_confirmada(lead)
            elif notif["tipo"] == "alerta_interno":
                subject, html = email_service.build_internal_alert(
                    lead, lead.get("motivo_status") or "Lead qualificado pelo agente"
                )
            else:
                subject, html = email_service.build_reminder(lead, notif["tipo"])

            email_service.send_email(notif["destinatario"], subject, html)
            supabase.table("notifications").update(
                {
                    "status": "enviada",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", notif["id"]).execute()
            enviadas += 1
        except Exception as exc:
            logger.exception("Falha ao enviar notificação %s", notif["id"])
            supabase.table("notifications").update(
                {"status": "falha", "error": str(exc)[:500]}
            ).eq("id", notif["id"]).execute()
            falhas += 1

    return NotificationsRunResult(
        processadas=len(due.data or []), enviadas=enviadas, falhas=falhas
    )
