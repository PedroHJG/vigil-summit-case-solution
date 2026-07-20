"""Régua proativa anti no-show (meta: comparecimento > 70%).

Sequência de toques de WhatsApp entre a inscrição e o dia do evento, decidida
aqui (o n8n só chama POST /internal/cadence/run em cron horário).

REGRAS DE NEGÓCIO (racional de cada uma):

Para QUALIFICADOS que não confirmaram (recuperar a confirmação):
  - nudge_confirm_1: 24h após qualificar sem resposta — prova social.
    (24h respeita o tempo do executivo; prova social > repetir o pedido.)
  - nudge_confirm_2: 48h após o 1º nudge — escassez honesta (+ botão de novo).
  - last_call: D-2 — última chamada; transparência de que a vaga será liberada.
  - Expurgo: 24h após o last_call sem resposta -> status 'perdido' (libera vaga
    e tira o lead de réguas futuras; base limpa = métrica de presença honesta).

Para CONFIRMADOS (reduzir no-show e criar antecipação):
  - companion  (D-7): convite para até 2 acompanhantes. Quem leva alguém tem
    compromisso social com a própria presença — é o toque mais anti no-show.
  - content    (D-5): antecipação personalizada (conteúdo x dor da empresa,
    vinda do enriquecimento) — relevância, não lembrete.
  - logistics  (D-1): véspera com logística + pedido de OK (micro-compromisso).
  - day_of     (H-3): lembrete curtíssimo no dia.

Regras transversais:
  - Mensagem adaptativa: cada toque informa ao agente se o anterior foi
    respondido; se não foi, o agente MUDA O ÂNGULO em vez de repetir.
  - Janela de envio: 08h–20h (America/Sao_Paulo). Fora dela, o toque espera o
    próximo ciclo do cron.
  - Frequência: máximo 1 toque proativo por lead a cada 20h.
  - Idempotência: unique(lead_id, touchpoint) no banco — cada toque sai 1 vez.
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from core.config import get_settings
from core.supabase_client import get_supabase
from services import lead_service

logger = logging.getLogger(__name__)

QUIET_START, QUIET_END = 20, 8      # sem toques entre 20h e 8h (hora local)
MIN_GAP_HOURS = 20                  # intervalo mínimo entre toques por lead
EXPIRE_AFTER_LAST_CALL_H = 24       # last_call sem resposta -> perdido


class CadenceRunResult(BaseModel):
    leads_avaliados: int
    toques_enviados: list[str] = []
    expurgados: list[str] = []
    detalhes: list[str] = []


def _dentro_da_janela(now_local: datetime) -> bool:
    return QUIET_END <= now_local.hour < QUIET_START


def next_touchpoint(
    status: str,
    dias_para_evento: float,
    horas_desde_qualificacao: float | None,
    enviados: dict[str, datetime],
    now: datetime,
) -> str | None:
    """Decide o próximo toque devido (função pura — regras testáveis).

    `enviados` mapeia touchpoint -> sent_at dos toques já feitos.
    """
    ultimo_envio = max(enviados.values()) if enviados else None
    if ultimo_envio and (now - ultimo_envio) < timedelta(hours=MIN_GAP_HOURS):
        return None  # respeita a frequência máxima

    if status == "qualificado":
        if "last_call" in enviados:
            return None
        if dias_para_evento <= 2:
            return "last_call"
        if "nudge_confirm_2" in enviados:
            return None
        if "nudge_confirm_1" in enviados:
            if now - enviados["nudge_confirm_1"] >= timedelta(hours=48):
                return "nudge_confirm_2"
            return None
        if horas_desde_qualificacao is not None and horas_desde_qualificacao >= 24:
            return "nudge_confirm_1"
        return None

    if status == "confirmado":
        horas_para_evento = dias_para_evento * 24
        if 0 < horas_para_evento <= 3 and "day_of" not in enviados:
            return "day_of"
        if 0 < dias_para_evento <= 1 and "logistics" not in enviados:
            return "logistics"
        if 0 < dias_para_evento <= 5 and "content" not in enviados:
            return "content"
        if 0 < dias_para_evento <= 7 and "companion" not in enviados:
            return "companion"
        return None

    return None


def _feedback_anterior(enviados_rows: list[dict]) -> str:
    if not enviados_rows:
        return "Este é o primeiro toque proativo."
    ultimo = max(enviados_rows, key=lambda r: r["sent_at"])
    if ultimo["respondido"]:
        return "O toque anterior foi respondido pelo lead."
    return (
        "O toque anterior NÃO foi respondido — mude completamente o ângulo da "
        "abordagem, não repita o argumento."
    )


def mark_last_touch_responded(lead_id: str) -> None:
    """Chamado quando o lead responde qualquer coisa no WhatsApp."""
    supabase = get_supabase()
    rows = (
        supabase.table("cadence_log")
        .select("id")
        .eq("lead_id", lead_id)
        .eq("respondido", False)
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
    )
    if rows.data:
        supabase.table("cadence_log").update({"respondido": True}).eq(
            "id", rows.data[0]["id"]
        ).execute()


def run_cadence() -> CadenceRunResult:
    from agent.prompts import CADENCE_KICKOFFS
    from services import agent_service

    settings = get_settings()
    tz = ZoneInfo(settings.meeting_timezone)
    now = datetime.now(timezone.utc)
    now_local = now.astimezone(tz)
    supabase = get_supabase()

    resultado = CadenceRunResult(leads_avaliados=0)

    if not _dentro_da_janela(now_local):
        resultado.detalhes.append("Fora da janela 08h-20h; nenhum toque enviado.")
        return resultado

    event_date = settings.event_date.astimezone(timezone.utc)
    if now >= event_date:
        resultado.detalhes.append("Evento já ocorreu; régua pré-evento encerrada.")
        return resultado

    dias_para_evento = (event_date - now).total_seconds() / 86400

    leads = (
        supabase.table("leads")
        .select("*")
        .in_("status", ["qualificado", "confirmado"])
        .execute()
        .data
        or []
    )
    resultado.leads_avaliados = len(leads)

    for lead in leads:
        log_rows = (
            supabase.table("cadence_log")
            .select("*")
            .eq("lead_id", lead["id"])
            .execute()
            .data
            or []
        )
        enviados = {
            r["touchpoint"]: datetime.fromisoformat(r["sent_at"]) for r in log_rows
        }

        # Expurgo: last_call vencido sem resposta -> perdido (libera a vaga)
        if lead["status"] == "qualificado" and "last_call" in enviados:
            row_last = next(r for r in log_rows if r["touchpoint"] == "last_call")
            vencido = now - enviados["last_call"] >= timedelta(hours=EXPIRE_AFTER_LAST_CALL_H)
            if vencido and not row_last["respondido"]:
                lead_service.update_status(
                    lead["id"], "perdido", "Sem resposta à régua de confirmação"
                )
                resultado.expurgados.append(lead["id"])
                continue

        horas_desde_qualificacao = None
        if lead["status"] == "qualificado" and lead.get("updated_at"):
            horas_desde_qualificacao = (
                now - datetime.fromisoformat(lead["updated_at"])
            ).total_seconds() / 3600

        touchpoint = next_touchpoint(
            lead["status"], dias_para_evento, horas_desde_qualificacao, enviados, now
        )
        if not touchpoint:
            continue

        kickoff = CADENCE_KICKOFFS[touchpoint].format(
            feedback_anterior=_feedback_anterior(log_rows)
        )
        try:
            agent_service.send_proactive_touch(lead, kickoff)
        except Exception as exc:
            logger.exception("Falha no toque %s do lead %s", touchpoint, lead["id"])
            resultado.detalhes.append(f"{lead['id']}/{touchpoint}: {exc}")
            continue

        supabase.table("cadence_log").upsert(
            {"lead_id": lead["id"], "touchpoint": touchpoint},
            on_conflict="lead_id,touchpoint",
            ignore_duplicates=True,
        ).execute()
        lead_service.log_event(lead["id"], "cadence_touch", {"touchpoint": touchpoint})
        resultado.toques_enviados.append(f"{lead['id']}:{touchpoint}")

    return resultado