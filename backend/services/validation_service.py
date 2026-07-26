"""Watcher da curadoria humana (Google Sheets).

Chamado em cron pelo n8n (POST /internal/validations/run). Para cada lead em
'aguardando_validacao', lê a planilha; quando o humano marcou validado="sim",
resolve o cargo e dispara o reengajamento do agente para levar o lead à
confirmação da inscrição.

Regra do cargo:
1. cargo preenchido pelo curador na planilha  -> usa esse;
2. planilha vazia e cargo do formulário != 'Outros' -> usa o do formulário;
3. planilha vazia e formulário = 'Outros' -> o agente pergunta na conversa.
"""

import logging

from pydantic import BaseModel

from agent.tools import sheets
from services import lead_service

logger = logging.getLogger(__name__)


class ValidationRunResult(BaseModel):
    verificados: int
    reengajados: list[str] = []
    desqualificados: list[str] = []
    detalhes: list[str] = []


def run_validation_checks() -> ValidationRunResult:
    from services import agent_service  # import tardio (evita ciclo)

    from core.supabase_client import get_supabase

    pendentes = lead_service.list_leads_by_status("aguardando_validacao")
    reengajados: list[str] = []
    desqualificados: list[str] = []
    detalhes: list[str] = []

    for lead in pendentes:
        try:
            validacao = sheets.read_validation(lead["telefone_e164"])
        except FileNotFoundError:
            detalhes.append("Credencial do Google não configurada; watcher inativo.")
            break
        except Exception as exc:
            logger.warning("Falha ao ler planilha p/ lead %s: %s", lead["id"], exc)
            detalhes.append(f"{lead['id']}: planilha indisponível ({exc})")
            continue

        if not validacao["encontrado"]:
            detalhes.append(f"{lead['id']}: ainda sem linha na planilha")
            continue
        if not validacao["validado"]:
            continue  # humano ainda não aprovou

        cargo_planilha = validacao.get("cargo")
        if cargo_planilha:
            cargo_final = cargo_planilha
            perguntar_cargo = False
        elif lead["cargo"] != "Outros":
            cargo_final = lead["cargo"]
            perguntar_cargo = False
        else:
            cargo_final = None
            perguntar_cargo = True

        # O "validado=sim" do humano é necessário, mas NÃO suficiente: os
        # requisitos duros do ICP (cargo decisor + porte 200+) são conferidos
        # aqui. Setor não elimina (só ajusta o score). Usa o cargo já resolvido.
        lead_para_icp = {**lead, "cargo_validado": cargo_final or lead.get("cargo_validado")}
        passou_icp, motivo_icp = lead_service.checar_icp(lead_para_icp)
        if not passou_icp:
            get_supabase().table("leads").update(
                {"status": "desqualificado", "motivo_status": f"Fora do ICP: {motivo_icp}"}
            ).eq("id", lead["id"]).execute()
            lead_service.log_event(
                lead["id"], "desqualificado_icp", {"motivo": motivo_icp}
            )
            # Feedback amigável ao lead — não deixá-lo sem retorno após a curadoria.
            agent_service.enviar_feedback_desqualificacao(lead)
            desqualificados.append(lead["id"])
            detalhes.append(f"{lead['id']}: desqualificado — {motivo_icp}")
            continue

        # Se o evento já está lotado, não há vaga para reengajar/confirmar —
        # o lead fica qualificado (lista de espera implícita) sem ser reengajado.
        if lead_service.evento_lotado():
            get_supabase().table("leads").update(
                {"status": "qualificado", "cargo_validado": cargo_final,
                 "motivo_status": "Aprovado, mas evento lotado (lista de espera)"}
            ).eq("id", lead["id"]).execute()
            lead_service.log_event(lead["id"], "aprovado_sem_vaga", {})
            detalhes.append(f"{lead['id']}: aprovado, mas sem vaga (evento lotado)")
            continue

        update: dict = {
            "status": "qualificado",
            "motivo_status": "Curadoria validou o LinkedIn + ICP conferido",
        }
        if cargo_final:
            update["cargo_validado"] = cargo_final
        get_supabase().table("leads").update(update).eq("id", lead["id"]).execute()
        lead_service.log_event(
            lead["id"],
            "validacao_aprovada",
            {"cargo_final": cargo_final, "perguntar_cargo": perguntar_cargo},
        )

        try:
            agent_service.reengage_after_validation(lead["id"], perguntar_cargo)
            reengajados.append(lead["id"])
        except Exception as exc:
            logger.exception("Falha no reengajamento do lead %s", lead["id"])
            detalhes.append(f"{lead['id']}: reengajamento falhou ({exc})")

    return ValidationRunResult(
        verificados=len(pendentes),
        reengajados=reengajados,
        desqualificados=desqualificados,
        detalhes=detalhes,
    )