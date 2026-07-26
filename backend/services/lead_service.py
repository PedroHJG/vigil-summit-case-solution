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


# =============================================================================
# ICP (perfil-alvo do RAG) e capacidade do evento
# =============================================================================

# Cargos-alvo do formulário que já contam como decisor de segurança/TI.
CARGOS_DECISORES = {"CTO", "CISO", "Diretor de TI", "Gestor de Risco"}
# Palavras que indicam cargo decisor quando o curador preenche texto livre
# (ex.: "Head de Segurança", "CIO", "VP de Tecnologia").
_DECISOR_KEYWORDS = (
    "ciso", "cto", "cio", "cso", "diretor", "diretora", "head", "chief",
    "vp", "vice-presidente", "gerente de seguran", "gerente de risco",
    "gerente de ti", "coordenador de seguran", "superintendente",
)

# Status que já ocupam uma vaga garantida no evento.
STATUS_COM_VAGA = {
    "confirmado", "compareceu", "ausente", "em_follow_up", "reuniao_agendada",
}


def is_decisor(cargo: str | None) -> bool:
    """True se o cargo indica um decisor de segurança/TI (elegível ao ICP)."""
    if not cargo:
        return False
    if cargo in CARGOS_DECISORES:
        return True
    c = cargo.strip().lower()
    return any(k in c for k in _DECISOR_KEYWORDS)


def parse_funcionarios(valor) -> int | None:
    """'850', 'entre 200 e 500', '1.200+' -> maior número encontrado (ou None)."""
    if valor is None:
        return None
    numeros = re.findall(r"\d+", str(valor).replace(".", ""))
    return max(int(n) for n in numeros) if numeros else None


def checar_icp(lead: dict, min_funcionarios: int = 200) -> tuple[bool, str]:
    """Aplica os requisitos DUROS do RAG (cargo decisor + porte 200+).

    Setor NÃO é eliminatório (só ajusta o score). Retorna (passou, motivo).
    Dado faltante de porte não elimina (benefício da dúvida — o humano validou).
    """
    cargo = lead.get("cargo_validado") or lead.get("cargo")
    if not is_decisor(cargo):
        return False, f"Cargo '{cargo}' não é decisor de segurança/TI (fora do ICP)."

    func = parse_funcionarios(lead.get("funcionarios"))
    if func is not None and func < min_funcionarios:
        return False, f"Empresa com {func} funcionários (< {min_funcionarios}, fora do ICP)."

    return True, "Atende ao ICP (cargo decisor e porte)."


def contar_vagas_ocupadas() -> int:
    """Nº de leads que já ocupam uma vaga (confirmados e além)."""
    supabase = get_supabase()
    resp = (
        supabase.table("leads")
        .select("id", count="exact")
        .in_("status", list(STATUS_COM_VAGA))
        .execute()
    )
    return resp.count or 0


def vagas_disponiveis() -> int:
    """Vagas restantes (capacidade - ocupadas). Nunca negativo."""
    from core.config import get_settings

    return max(0, get_settings().event_capacity - contar_vagas_ocupadas())


def evento_lotado() -> bool:
    return vagas_disponiveis() <= 0


def tem_vaga_garantida(lead: dict) -> bool:
    return lead.get("status") in STATUS_COM_VAGA


# =============================================================================
# Moderação de contexto (anti-abuso / economia de tokens)
# =============================================================================

def _parse_ts(valor) -> "datetime | None":
    from datetime import datetime

    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None


def bloqueio_ativo(lead: dict) -> bool:
    """True se o atendimento automático do lead está bloqueado agora."""
    from datetime import datetime, timezone

    ate = _parse_ts(lead.get("bloqueado_ate"))
    return ate is not None and ate > datetime.now(timezone.utc)


def registrar_offtopic(lead_id: str) -> int:
    """Incrementa o contador de off-topic consecutivas e retorna o novo valor."""
    supabase = get_supabase()
    atual = (
        supabase.table("leads").select("off_topic_streak").eq("id", lead_id).execute()
    )
    novo = ((atual.data[0].get("off_topic_streak") or 0) if atual.data else 0) + 1
    supabase.table("leads").update({"off_topic_streak": novo}).eq("id", lead_id).execute()
    return novo


def resetar_offtopic(lead_id: str) -> None:
    get_supabase().table("leads").update({"off_topic_streak": 0}).eq(
        "id", lead_id
    ).execute()


def bloquear_lead(lead_id: str, horas: int) -> None:
    """Bloqueia o atendimento automático por N horas e zera o contador."""
    from datetime import datetime, timedelta, timezone

    ate = datetime.now(timezone.utc) + timedelta(hours=horas)
    get_supabase().table("leads").update(
        {"bloqueado_ate": ate.isoformat(), "off_topic_streak": 0}
    ).eq("id", lead_id).execute()
    log_event(lead_id, "bloqueado_offtopic", {"ate": ate.isoformat(), "horas": horas})


def limpar_bloqueio(lead_id: str) -> None:
    get_supabase().table("leads").update(
        {"bloqueado_ate": None, "off_topic_streak": 0}
    ).eq("id", lead_id).execute()
