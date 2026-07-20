"""Regras de negócio de leads: normalização, persistência e transições de funil."""

import logging
import re

from fastapi import HTTPException, status

from api.schemas import LeadCreate
from core.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def normalize_phone_e164(ddi: str, telefone: str) -> str:
    """"+55" + "(11) 9 9999-9999" -> "+5511999999999"."""
    ddi_digits = re.sub(r"\D", "", ddi)
    tel_digits = re.sub(r"\D", "", telefone)
    return f"+{ddi_digits}{tel_digits}"


def domain_from_email(email: str) -> str:
    return email.split("@")[1].lower()


def create_lead(payload: LeadCreate) -> dict:
    supabase = get_supabase()

    existing = (
        supabase.table("leads").select("id").eq("email", payload.email).execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está inscrito no evento.",
        )

    row = {
        "nome": payload.nome,
        "email": payload.email,
        "ddi": payload.ddi,
        "telefone": payload.telefone,
        "telefone_e164": normalize_phone_e164(payload.ddi, payload.telefone),
        "cargo": payload.cargo.value,
        "empresa": payload.empresa,
        "dominio_empresa": domain_from_email(payload.email),
        "status": "novo",
    }
    result = supabase.table("leads").insert(row).execute()
    lead = result.data[0]
    log_event(lead["id"], "lead_criado", {"origem": "landing_page"})
    return lead


def get_lead(lead_id: str) -> dict:
    supabase = get_supabase()
    result = supabase.table("leads").select("*").eq("id", lead_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    return result.data[0]


def get_lead_by_phone(phone_e164: str) -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("leads").select("*").eq("telefone_e164", phone_e164).execute()
    )
    if result.data:
        return result.data[0]
        
    # Tratamento para o nono dígito do Brasil (+55)
    if phone_e164.startswith("+55"):
        alt_phone = None
        # Se veio com 13 caracteres ex: +551199999999, o len é 13, tenta adicionar o 9 -> +5511999999999
        if len(phone_e164) == 13:
            alt_phone = f"+55{phone_e164[3:5]}9{phone_e164[5:]}"
        # Se veio com 14 caracteres ex: +5511999999999, tenta remover o 9
        elif len(phone_e164) == 14 and phone_e164[5] == "9":
            alt_phone = f"+55{phone_e164[3:5]}{phone_e164[6:]}"
            
        if alt_phone:
            result_alt = supabase.table("leads").select("*").eq("telefone_e164", alt_phone).execute()
            if result_alt.data:
                return result_alt.data[0]
                
    return None


def update_status(lead_id: str, novo_status: str, motivo: str | None = None) -> None:
    supabase = get_supabase()
    update: dict = {"status": novo_status}
    if motivo:
        update["motivo_status"] = motivo
    supabase.table("leads").update(update).eq("id", lead_id).execute()
    log_event(lead_id, "status_change", {"novo_status": novo_status, "motivo": motivo})


def list_leads_by_status(status_lead: str) -> list[dict]:
    supabase = get_supabase()
    result = supabase.table("leads").select("*").eq("status", status_lead).execute()
    return result.data or []


def log_event(lead_id: str | None, event_type: str, payload: dict) -> None:
    """Trilha de auditoria; nunca deve derrubar o fluxo principal."""
    try:
        get_supabase().table("agent_events").insert(
            {"lead_id": lead_id, "event_type": event_type, "payload": payload}
        ).execute()
    except Exception:
        logger.exception("Falha ao registrar agent_event %s", event_type)
