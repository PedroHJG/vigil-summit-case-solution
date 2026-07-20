"""Configurações centralizadas do backend (12-factor, via variáveis de ambiente)."""

from datetime import datetime
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Aplicação -----------------------------------------------------------
    app_name: str = "Vigil Summit AI Backend"
    app_version: str = "1.0.0"
    # Chave exigida nos endpoints internos (chamados pelo n8n) via header X-API-Key
    backend_api_key: str = "change-me"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Supabase ------------------------------------------------------------
    supabase_url: str = ""
    supabase_service_key: str = ""
    # Connection string Postgres do Supabase (Session pooler) — usada pelo
    # LangChain (PostgresChatMessageHistory) para a memória das conversas.
    database_url: str = ""

    # --- Anthropic / LangChain -----------------------------------------------
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    anthropic_max_tokens: int = 1024

    # --- Evolution API (WhatsApp) ---------------------------------------------
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_instance: str = "vigil"

    # --- Google (Sheets human-in-the-loop + Calendar) --------------------------
    google_service_account_file: str = "credentials/service_account.json"
    # OAuth do DONO da agenda (recomendado p/ Calendar): permite convidar o lead
    # (evento entra na agenda dele) e ler o free/busy real. Gere o token com
    # `python -m scripts.google_oauth_setup`.
    google_oauth_client_file: str = "credentials/oauth_client.json"
    google_oauth_token_file: str = "credentials/google_oauth_token.json"
    google_sheets_id: str = ""
    google_sheets_worksheet: str = "Validacao"
    google_calendar_id: str = "primary"

    # --- Agenda de reuniões (pós-evento) -----------------------------------------
    meeting_timezone: str = "America/Sao_Paulo"
    meeting_business_start_hour: int = 9
    meeting_business_end_hour: int = 18
    meeting_min_lead_days: int = 2      # propor horários a partir de D+2
    meeting_search_days: int = 10       # janela de busca de disponibilidade

    # --- E-mail (SMTP Gmail) ---------------------------------------------------
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""          # app password do Gmail
    smtp_from: str = ""
    sales_alert_email: str = ""      # destinatário dos alertas internos
    email_mock_mode: bool = False    # True => não envia; apenas loga (demo sem credenciais)

    # --- Evento ----------------------------------------------------------------
    event_name: str = "Vigil Summit — Segurança para a Era da IA"
    event_date: datetime = datetime.fromisoformat("2026-08-20T09:00:00-03:00")
    event_location: str = "São Paulo, SP"
    event_landing_url: str = "http://localhost:5173"

    # --- Scraper ----------------------------------------------------------------
    scraper_timeout_seconds: float = 10.0
    scraper_max_pages: int = 4
    scraper_max_chars: int = 12000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
