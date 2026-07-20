"""Rotas públicas de leads (consumidas pela landing page)."""

from fastapi import APIRouter, status

from api.schemas import LeadCreate, LeadCreatedResponse, LeadOut
from services import lead_service, notification_service

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.post("", response_model=LeadCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate) -> LeadCreatedResponse:
    """Recebe a inscrição da landing page, valida e persiste no Supabase.

    A inserção com status='novo' é o gatilho do funil: o n8n detecta o registro
    (polling) e roteia enriquecimento + engajamento. A régua de e-mails do lead
    é agendada aqui (envio efetivo acontece no cron de notificações).
    """
    lead = lead_service.create_lead(payload)
    notification_service.schedule_for_lead(lead)
    return LeadCreatedResponse(id=lead["id"], status=lead["status"])


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str) -> dict:
    return lead_service.get_lead(lead_id)
