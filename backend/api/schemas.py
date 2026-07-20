"""Contratos de API (Pydantic) do backend Vigil Summit.

Espelham as validações do formulário da landing page e definem os payloads
trocados com o n8n (roteador) e com a Evolution API (webhook de WhatsApp).
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

# Mesma lista de domínios gratuitos bloqueados no frontend (InscricaoSection.tsx)
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.com.br", "hotmail.com",
    "outlook.com", "uol.com.br", "bol.com.br", "icloud.com",
    "msn.com", "live.com", "terra.com.br", "ig.com.br",
}


class CargoLead(str, Enum):
    CTO = "CTO"
    CISO = "CISO"
    DIRETOR_TI = "Diretor de TI"
    GESTOR_RISCO = "Gestor de Risco"
    OUTROS = "Outros"


class StatusLead(str, Enum):
    NOVO = "novo"
    ENRIQUECENDO = "enriquecendo"
    ENRIQUECIDO = "enriquecido"
    EM_CONVERSA = "em_conversa"
    AGUARDANDO_VALIDACAO = "aguardando_validacao"
    QUALIFICADO = "qualificado"
    DESQUALIFICADO = "desqualificado"
    CONFIRMADO = "confirmado"
    COMPARECEU = "compareceu"
    AUSENTE = "ausente"
    EM_FOLLOW_UP = "em_follow_up"
    REUNIAO_AGENDADA = "reuniao_agendada"
    PERDIDO = "perdido"


# =============================================================================
# Leads (landing page -> backend)
# =============================================================================

class LeadCreate(BaseModel):
    """Payload enviado pelo formulário da landing page."""

    nome: str = Field(min_length=3, max_length=160)
    email: EmailStr
    ddi: str = Field(default="+55", pattern=r"^\+\d{1,3}$")
    telefone: str = Field(min_length=8, max_length=25)
    cargo: CargoLead
    empresa: str = Field(min_length=2, max_length=160)

    @field_validator("nome")
    @classmethod
    def nome_completo(cls, v: str) -> str:
        v = v.strip()
        if len(v.split()) < 2:
            raise ValueError("Informe nome e sobrenome.")
        return v

    @field_validator("email")
    @classmethod
    def email_corporativo(cls, v: str) -> str:
        dominio = v.split("@")[1].lower()
        if dominio in FREE_EMAIL_DOMAINS:
            raise ValueError(
                "Utilize um e-mail corporativo (Gmail, Outlook etc. não são aceitos)."
            )
        return v.lower()

    @field_validator("telefone")
    @classmethod
    def telefone_valido(cls, v: str) -> str:
        digitos = re.sub(r"\D", "", v)
        # Celular BR: DDD (2) + 9 dígitos; aceita fixo (10) para outros DDIs
        if not 10 <= len(digitos) <= 13:
            raise ValueError("Telefone inválido. Use o formato (11) 9 9999-9999.")
        return v

    @field_validator("empresa")
    @classmethod
    def empresa_limpa(cls, v: str) -> str:
        return v.strip()


class LeadOut(BaseModel):
    id: UUID
    nome: str
    email: str
    ddi: str
    telefone: str
    telefone_e164: str
    cargo: str
    empresa: str
    dominio_empresa: str | None = None
    status: str
    linkedin_url: str | None = None
    cargo_validado: str | None = None
    lead_score: int | None = None
    created_at: datetime
    updated_at: datetime


class LeadCreatedResponse(BaseModel):
    id: UUID
    status: str
    message: str = "Inscrição recebida com sucesso."


# =============================================================================
# Endpoints internos (n8n atua apenas como roteador destes endpoints)
# =============================================================================

class EnrichmentResult(BaseModel):
    lead_id: UUID
    status: str                      # 'sucesso' | 'falha'
    website_url: str | None = None
    pages_scraped: list[str] = []
    summary: str | None = None
    industry: str | None = None
    company_size_hint: str | None = None
    error: str | None = None


class EngageResult(BaseModel):
    lead_id: UUID
    conversation_id: UUID
    session_id: UUID
    mensagem_inicial: str


class NotificationsRunResult(BaseModel):
    processadas: int
    enviadas: int
    falhas: int


class FollowUpRunResult(BaseModel):
    leads_processados: list[UUID]
    detalhes: list[str] = []


# =============================================================================
# Webhook da Evolution API (mensagens recebidas no WhatsApp)
# =============================================================================

class EvolutionWebhookPayload(BaseModel):
    """Envelope enviado pela Evolution API v2 (evento messages.upsert).

    O payload real é grande e variável; validamos de forma leniente e a
    extração fina fica em WhatsAppService.parse_incoming().
    """

    event: str = ""
    instance: str = ""
    data: dict[str, Any] = {}


class IncomingMessage(BaseModel):
    """Mensagem de WhatsApp já normalizada para consumo interno."""

    phone_e164: str          # +5511999999999
    text: str
    message_id: str | None = None
    push_name: str | None = None
    button_id: str | None = None   # id do botão/linha clicado (mensagens interativas)


class WebhookAck(BaseModel):
    status: str              # 'processed' | 'ignored'
    detail: str | None = None


# =============================================================================
# Saúde
# =============================================================================

class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
