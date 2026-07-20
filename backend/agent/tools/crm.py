"""Tool de escrita no CRM (Supabase): transições de status feitas pelo agente."""

import json
import logging

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Estados que o AGENTE pode atribuir (subconjunto do enum status_lead;
# transições operacionais como 'enriquecendo' são exclusivas do backend).
AGENT_ALLOWED_STATUSES = {
    "aguardando_validacao",
    "qualificado",
    "desqualificado",
    "confirmado",
    "reuniao_agendada",
    "perdido",
}


class AtualizarStatusArgs(BaseModel):
    novo_status: str = Field(
        description=(
            "Um destes valores: aguardando_validacao, qualificado, desqualificado, "
            "confirmado, reuniao_agendada, perdido"
        )
    )
    motivo: str = Field(description="Justificativa curta da mudança (1 frase).")
    linkedin_url: str | None = Field(
        default=None, description="URL do LinkedIn informada pelo lead, se houver."
    )
    lead_score: int | None = Field(
        default=None, ge=0, le=100, description="Score de 0 a 100 ao qualificar."
    )
    cargo_confirmado: str | None = Field(
        default=None,
        description="Cargo do lead confirmado na conversa (quando o formulário era 'Outros').",
    )


def atualizar_status_lead(
    lead_id: str,
    novo_status: str,
    motivo: str,
    linkedin_url: str | None = None,
    lead_score: int | None = None,
    cargo_confirmado: str | None = None,
) -> str:
    if novo_status not in AGENT_ALLOWED_STATUSES:
        return json.dumps(
            {
                "erro": f"Status '{novo_status}' não permitido.",
                "permitidos": sorted(AGENT_ALLOWED_STATUSES),
            },
            ensure_ascii=False,
        )

    # Nunca deixa uma falha de banco derrubar o turno do agente (o lead ficaria
    # sem resposta): erros viram JSON e o agente segue a conversa.
    try:
        supabase = get_supabase()
        update: dict = {"status": novo_status, "motivo_status": motivo}
        if linkedin_url:
            update["linkedin_url"] = linkedin_url
        if lead_score is not None:
            update["lead_score"] = lead_score
        if cargo_confirmado:
            update["cargo_validado"] = cargo_confirmado

        supabase.table("leads").update(update).eq("id", lead_id).execute()
        supabase.table("agent_events").insert(
            {
                "lead_id": lead_id,
                "event_type": "status_change_agente",
                "payload": {"novo_status": novo_status, "motivo": motivo},
            }
        ).execute()
    except Exception as exc:
        logger.exception("Falha ao atualizar status do lead %s", lead_id)
        return json.dumps(
            {"erro": f"Não foi possível registrar agora ({exc}). Siga a conversa normalmente."},
            ensure_ascii=False,
        )
    logger.info("Lead %s -> %s (%s)", lead_id, novo_status, motivo)

    return json.dumps({"status": "ok", "novo_status": novo_status}, ensure_ascii=False)


class RegistrarAcompanhantesArgs(BaseModel):
    quantidade: int = Field(
        ge=0, le=2, description="Quantidade de acompanhantes que o lead levará (0 a 2)."
    )


def make_acompanhantes_tool(lead_id: str) -> StructuredTool:
    """Tool que registra quantos acompanhantes o lead levará (máximo 2)."""

    def _registrar(quantidade: int) -> str:
        try:
            supabase = get_supabase()
            supabase.table("leads").update({"acompanhantes": quantidade}).eq(
                "id", lead_id
            ).execute()
            supabase.table("agent_events").insert(
                {
                    "lead_id": lead_id,
                    "event_type": "acompanhantes_registrados",
                    "payload": {"quantidade": quantidade},
                }
            ).execute()
        except Exception as exc:
            logger.exception("Falha ao registrar acompanhantes do lead %s", lead_id)
            return json.dumps(
                {"erro": f"Não foi possível registrar agora ({exc}). Avise que a organização confirmará os assentos."},
                ensure_ascii=False,
            )
        return json.dumps(
            {"status": "ok", "acompanhantes": quantidade,
             "detalhe": f"{quantidade} assento(s) de acompanhante garantido(s)."},
            ensure_ascii=False,
        )

    return StructuredTool.from_function(
        func=_registrar,
        name="registrar_acompanhantes",
        description=(
            "Registra a quantidade de acompanhantes (0 a 2) que o lead levará ao "
            "evento. Use quando o lead disser quantas pessoas quer levar. O limite "
            "é 2; se ele pedir mais, registre 2 e explique o limite da curadoria."
        ),
        args_schema=RegistrarAcompanhantesArgs,
    )


def make_crm_tool(lead_id: str) -> StructuredTool:
    """Cria a tool de atualização de status já amarrada ao lead da conversa."""

    def _atualizar(
        novo_status: str,
        motivo: str,
        linkedin_url: str | None = None,
        lead_score: int | None = None,
        cargo_confirmado: str | None = None,
    ) -> str:
        return atualizar_status_lead(
            lead_id, novo_status, motivo, linkedin_url, lead_score, cargo_confirmado
        )

    return StructuredTool.from_function(
        func=_atualizar,
        name="atualizar_status_lead",
        description=(
            "Atualiza o estágio deste lead no funil do CRM. Use nos momentos "
            "definidos nas suas instruções (LinkedIn recebido, qualificação, "
            "confirmação de presença, reunião agendada, desistência/optout)."
        ),
        args_schema=AtualizarStatusArgs,
    )
