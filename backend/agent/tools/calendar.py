"""Tools de Google Calendar: disponibilidade e agendamento (pós-evento).

Autenticação (ordem de preferência):
1. OAuth do DONO da agenda (credentials/google_oauth_token.json — gere com
   `python -m scripts.google_oauth_setup`). Permite CONVIDAR o lead (o evento
   entra na agenda dele automaticamente) e ler o free/busy real do dono.
2. Service account (fallback): cria o evento, mas o Google bloqueia convite a
   participantes sem domain-wide delegation — o lead recebe só o link
   'adicionar à agenda' por e-mail/WhatsApp.

Disponibilidade "de ambos": a agenda do DONO é consultada via freebusy; a do
lead não é acessível sem autorização dele, então a disponibilidade dele é
negociada na conversa — o agente só propõe horários em que o dono está livre
e o lead escolhe o que serve para ele.
"""

import json
import logging
from datetime import datetime, time, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from core.config import get_settings
from core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _credentials():
    settings = get_settings()
    token_path = Path(settings.google_oauth_token_file)
    if token_path.exists():
        creds = UserCredentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds
    return service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )


@lru_cache
def _calendar_service():
    return build("calendar", "v3", credentials=_credentials(), cache_discovery=False)


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, HttpError) and exc.resp.status in (429, 500, 503)


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def _insert_event(body: dict, send_updates: str) -> dict:
    settings = get_settings()
    return (
        _calendar_service()
        .events()
        .insert(
            calendarId=settings.google_calendar_id,
            body=body,
            sendUpdates=send_updates,
        )
        .execute()
    )


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def _freebusy(time_min: datetime, time_max: datetime) -> list[tuple[datetime, datetime]]:
    """Períodos ocupados na agenda do dono (UTC-aware)."""
    settings = get_settings()
    resp = (
        _calendar_service()
        .freebusy()
        .query(
            body={
                "timeMin": time_min.astimezone(timezone.utc).isoformat(),
                "timeMax": time_max.astimezone(timezone.utc).isoformat(),
                "items": [{"id": settings.google_calendar_id}],
            }
        )
        .execute()
    )
    busy = resp["calendars"][settings.google_calendar_id].get("busy", [])
    return [
        (
            datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
            datetime.fromisoformat(b["end"].replace("Z", "+00:00")),
        )
        for b in busy
    ]


def _compute_free_slots(
    busy: list[tuple[datetime, datetime]],
    day_start: datetime,
    day_end: datetime,
    duracao: timedelta,
    step: timedelta = timedelta(minutes=30),
) -> list[datetime]:
    """Inícios livres dentro de [day_start, day_end] (função pura, testável)."""
    slots = []
    cursor = day_start
    while cursor + duracao <= day_end:
        fim = cursor + duracao
        if all(fim <= b_start or cursor >= b_end for b_start, b_end in busy):
            slots.append(cursor)
        cursor += step
    return slots


def find_free_slots(duracao_minutos: int = 45, max_slots: int = 6) -> list[datetime]:
    """Horários livres do dono em horário comercial, a partir de D+2 (dias úteis)."""
    settings = get_settings()
    tz = ZoneInfo(settings.meeting_timezone)
    hoje = datetime.now(tz).date()
    duracao = timedelta(minutes=duracao_minutos)

    inicio_busca = hoje + timedelta(days=settings.meeting_min_lead_days)
    fim_busca = inicio_busca + timedelta(days=settings.meeting_search_days)
    busy = _freebusy(
        datetime.combine(inicio_busca, time(0, 0), tz),
        datetime.combine(fim_busca, time(23, 59), tz),
    )

    slots: list[datetime] = []
    dia = inicio_busca
    while dia < fim_busca and len(slots) < max_slots:
        if dia.weekday() < 5:  # dias úteis
            day_start = datetime.combine(dia, time(settings.meeting_business_start_hour), tz)
            day_end = datetime.combine(dia, time(settings.meeting_business_end_hour), tz)
            livres = _compute_free_slots(busy, day_start, day_end, duracao)
            # No máximo 2 opções por dia, para espalhar as sugestões na semana
            slots.extend(livres[:2])
        dia += timedelta(days=1)
    return slots[:max_slots]


def _slot_disponivel(inicio: datetime, fim: datetime) -> bool:
    busy = _freebusy(inicio, fim)
    return all(fim <= b_start or inicio >= b_end for b_start, b_end in busy)


DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _fmt_slot(dt: datetime) -> dict:
    return {
        "iso": dt.isoformat(),
        "humano": f"{DIAS_PT[dt.weekday()]}, {dt.strftime('%d/%m')} às {dt.strftime('%Hh%M')}",
    }


def build_add_to_calendar_link(titulo: str, inicio: datetime, fim: datetime,
                               local: str, detalhes: str) -> str:
    """Link 'adicionar à agenda' do Google Calendar (não exige nenhuma API)."""
    from datetime import timezone as _tz
    from urllib.parse import quote

    fmt = "%Y%m%dT%H%M%SZ"
    inicio_utc = inicio.astimezone(_tz.utc).strftime(fmt)
    fim_utc = fim.astimezone(_tz.utc).strftime(fmt)
    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(titulo)}"
        f"&dates={inicio_utc}/{fim_utc}"
        f"&location={quote(local)}"
        f"&details={quote(detalhes)}"
    )


class AgendarReuniaoArgs(BaseModel):
    data_hora_inicio: str = Field(
        description=(
            "Início da reunião em ISO 8601 com offset, ex.: 2026-08-25T10:00:00-03:00"
        )
    )
    duracao_minutos: int = Field(default=45, ge=15, le=120)
    titulo: str | None = Field(
        default=None, description="Título opcional; se omitido, um padrão é usado."
    )


def criar_reuniao(
    lead: dict,
    data_hora_inicio: str,
    duracao_minutos: int = 45,
    titulo: str | None = None,
) -> str:
    """Cria o evento no Calendar, persiste em `meetings` e retorna JSON p/ o agente."""
    settings = get_settings()

    try:
        inicio = datetime.fromisoformat(data_hora_inicio)
    except ValueError:
        return json.dumps(
            {"erro": "data_hora_inicio inválida. Use ISO 8601, ex.: 2026-08-25T10:00:00-03:00"},
            ensure_ascii=False,
        )

    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=ZoneInfo(settings.meeting_timezone))
    fim = inicio + timedelta(minutes=duracao_minutos)

    # Agenda do dono é verificada ANTES de criar; se o horário foi ocupado
    # nesse meio-tempo, devolve alternativas reais para o agente propor.
    try:
        if not _slot_disponivel(inicio, fim):
            sugestoes = [_fmt_slot(s) for s in find_free_slots(duracao_minutos)]
            return json.dumps(
                {
                    "erro": "Este horário acabou de ficar indisponível na agenda do especialista.",
                    "horarios_disponiveis": sugestoes,
                },
                ensure_ascii=False,
            )
    except FileNotFoundError:
        return json.dumps(
            {"erro": "Credencial do Google não configurada; agendamento indisponível."},
            ensure_ascii=False,
        )
    except GoogleAuthError as exc:
        logger.error("Credencial do Google Calendar inválida/expirada: %s", exc)
        return json.dumps(
            {
                "erro": (
                    "A agenda do especialista está temporariamente indisponível "
                    "(credencial expirada). Diga ao lead que o time confirmará o "
                    "horário em breve por aqui mesmo."
                )
            },
            ensure_ascii=False,
        )
    except HttpError as exc:
        logger.warning("Freebusy falhou: %s (agendando sem checagem)", exc)

    titulo_final = titulo or (
        f"{settings.event_name} — Reunião com {lead['nome']} ({lead['empresa']})"
    )

    body = {
        "summary": titulo_final,
        "description": (
            f"Reunião comercial pós-evento com {lead['nome']} "
            f"({lead.get('cargo_validado') or lead['cargo']}) — {lead['empresa']}.\n"
            f"Contato: {lead['email']} | {lead['telefone_e164']}"
        ),
        "start": {"dateTime": inicio.isoformat()},
        "end": {"dateTime": fim.isoformat()},
        "attendees": [{"email": lead["email"]}],
    }

    try:
        try:
            event = _insert_event(body, send_updates="all")
        except HttpError as exc:
            # Service accounts sem domain-wide delegation não podem convidar
            # participantes: recria o evento sem attendees e segue o fluxo.
            if exc.resp.status == 403:
                body.pop("attendees", None)
                event = _insert_event(body, send_updates="none")
            else:
                raise
    except FileNotFoundError:
        return json.dumps(
            {"erro": "Credencial do Google não configurada; agendamento indisponível."},
            ensure_ascii=False,
        )
    except GoogleAuthError as exc:
        logger.error("Credencial do Google Calendar inválida/expirada: %s", exc)
        return json.dumps(
            {
                "erro": (
                    "A agenda do especialista está temporariamente indisponível "
                    "(credencial expirada). Diga ao lead que o time confirmará o "
                    "horário em breve por aqui mesmo."
                )
            },
            ensure_ascii=False,
        )
    except HttpError as exc:
        logger.warning("Google Calendar falhou após retries: %s", exc)
        return json.dumps(
            {"erro": "Agenda temporariamente indisponível. Proponha outro momento."},
            ensure_ascii=False,
        )

    supabase = get_supabase()
    supabase.table("meetings").insert(
        {
            "lead_id": lead["id"],
            "google_event_id": event.get("id"),
            "html_link": event.get("htmlLink"),
            "titulo": titulo_final,
            "start_time": inicio.isoformat(),
            "end_time": fim.isoformat(),
        }
    ).execute()

    convite_para_lead = "attendees" in body
    lembrete_link = build_add_to_calendar_link(
        titulo_final,
        inicio,
        fim,
        "Google Meet / a combinar",
        f"Reunião pós-{settings.event_name} com o especialista.",
    )
    return json.dumps(
        {
            "status": "agendada",
            "titulo": titulo_final,
            "quando": _fmt_slot(inicio)["humano"],
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "link": event.get("htmlLink"),
            "convite_na_agenda_do_lead": convite_para_lead,
            "link_lembrete_para_o_lead": lembrete_link,
            "detalhe": (
                "Reunião criada na agenda do especialista. "
                + ("O lead recebeu o convite por e-mail (basta aceitar para entrar na agenda dele); "
                   if convite_para_lead
                   else "O convite automático não pôde ser emitido; ")
                + "envie também o link_lembrete_para_o_lead pedindo que ele salve o lembrete na agenda."
            ),
        },
        ensure_ascii=False,
    )


class VerificarDisponibilidadeArgs(BaseModel):
    duracao_minutos: int = Field(default=45, ge=15, le=120)


def verificar_disponibilidade(duracao_minutos: int = 45) -> str:
    """Consulta o free/busy real do dono e devolve horários livres p/ propor."""
    try:
        slots = find_free_slots(duracao_minutos)
    except FileNotFoundError:
        return json.dumps(
            {"erro": "Credencial do Google não configurada; proponha horários e confirme depois."},
            ensure_ascii=False,
        )
    except GoogleAuthError as exc:
        logger.error("Credencial do Google Calendar inválida/expirada: %s", exc)
        return json.dumps(
            {
                "erro": (
                    "A agenda do especialista está temporariamente indisponível "
                    "(credencial expirada). Diga ao lead que o time confirmará o "
                    "horário em breve por aqui mesmo — não invente horários."
                )
            },
            ensure_ascii=False,
        )
    except HttpError as exc:
        logger.warning("Freebusy indisponível: %s", exc)
        return json.dumps(
            {"erro": "Agenda temporariamente indisponível; tente novamente em instantes."},
            ensure_ascii=False,
        )

    if not slots:
        return json.dumps(
            {"erro": "Sem horários livres na janela de busca; avise que o time retornará."},
            ensure_ascii=False,
        )
    return json.dumps(
        {"horarios_disponiveis": [_fmt_slot(s) for s in slots]},
        ensure_ascii=False,
    )


def make_disponibilidade_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=verificar_disponibilidade,
        name="verificar_disponibilidade",
        description=(
            "Consulta a agenda real do especialista e retorna os horários livres "
            "(dias úteis, horário comercial, a partir de dois dias úteis). Use ANTES "
            "de propor qualquer dia/horário de reunião ao lead."
        ),
        args_schema=VerificarDisponibilidadeArgs,
    )


def make_calendar_tool(lead: dict) -> StructuredTool:
    """Cria a tool de agendamento já amarrada ao lead da conversa."""

    def _agendar(data_hora_inicio: str, duracao_minutos: int = 45, titulo: str | None = None) -> str:
        return criar_reuniao(lead, data_hora_inicio, duracao_minutos, titulo)

    return StructuredTool.from_function(
        func=_agendar,
        name="agendar_reuniao",
        description=(
            "Agenda a reunião comercial no Google Calendar do especialista com "
            "convite para o lead. Use somente após o lead escolher explicitamente "
            "um dos horários confirmados como livres por verificar_disponibilidade. "
            "Se retornar conflito, proponha os horários alternativos devolvidos."
        ),
        args_schema=AgendarReuniaoArgs,
    )
