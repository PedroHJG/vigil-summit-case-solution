"""Endpoints internos — chamados exclusivamente pelo n8n (roteador).

Regra de arquitetura: o n8n NÃO contém lógica de negócio; ele apenas detecta
gatilhos (novo lead, cron) e chama estes endpoints. Toda a decisão fica aqui.
Autenticação via header X-API-Key (BACKEND_API_KEY).
"""

from fastapi import APIRouter, Depends

from api.deps import require_api_key
from api.schemas import (
    EngageResult,
    EnrichmentResult,
    FollowUpRunResult,
    NotificationsRunResult,
)
from services import agent_service, enrichment_service, notification_service
from services.cadence_service import CadenceRunResult, run_cadence
from services.validation_service import ValidationRunResult, run_validation_checks

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["internal (n8n)"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/leads/{lead_id}/enrich", response_model=EnrichmentResult)
def enrich(lead_id: str) -> EnrichmentResult:
    """Etapa 1 do funil: scraping do site da empresa + resumo estruturado."""
    return enrichment_service.enrich_lead(lead_id)


@router.post("/leads/{lead_id}/engage", response_model=EngageResult)
def engage(lead_id: str) -> EngageResult:
    """Etapa 2 do funil: agente inicia a qualificação via WhatsApp."""
    return agent_service.start_pre_event(lead_id)


@router.post("/cadence/run", response_model=CadenceRunResult)
def run_cadence_endpoint() -> CadenceRunResult:
    """Cron horário: régua proativa anti no-show (nudges, acompanhantes, D-1...)."""
    return run_cadence()


@router.post("/validations/run", response_model=ValidationRunResult)
def run_validations() -> ValidationRunResult:
    """Cron: verifica na planilha da curadoria quem foi validado e reengaja."""
    return run_validation_checks()


@router.post("/notifications/run", response_model=NotificationsRunResult)
def run_notifications() -> NotificationsRunResult:
    """Cron: envia os e-mails de lembrete/alerta vencidos."""
    return notification_service.run_due()


@router.post("/follow-ups/run", response_model=FollowUpRunResult)
def run_follow_ups() -> FollowUpRunResult:
    """Cron pós-evento: inicia follow-up comercial para quem compareceu."""
    return agent_service.run_follow_ups()
