"""Integração Human-in-the-loop via Google Sheets (leitura E escrita).

Fluxo:
1. Na qualificação, o AGENTE grava a linha de curadoria na planilha
   (tool `registrar_lead_curadoria`): nome, linkedin, whatsapp, empresa,
   quantidade de funcionários e validado="não" (cargo fica vazio p/ o humano).
2. O HUMANO analisa o LinkedIn, preenche a coluna cargo e muda validado="sim".
3. O watcher (services/validation_service.py) detecta o "sim" e o agente
   reengaja o lead para confirmar a inscrição.

Colunas esperadas na planilha (a busca é por palavra-chave normalizada, então
"Link do LinkedIn" ou "Quantidade de funcionários na empresa" funcionam):
| nome | link do linkedin | whatsapp | cargo | empresa | quantidade de funcionários | validado |
"""

import json
import logging
import unicodedata
from functools import lru_cache

import gspread
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import get_settings

logger = logging.getLogger(__name__)

# Palavra-chave (normalizada) que identifica cada coluna no cabeçalho
COLUMN_KEYWORDS = {
    "nome": "nome",
    "linkedin": "linkedin",
    "whatsapp": "whatsapp",
    "cargo": "cargo",
    "empresa": "empresa",
    "funcionarios": "funcion",
    "validado": "valid",
}

_retry_google = retry(
    retry=retry_if_exception_type(gspread.exceptions.APIError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)


@lru_cache
def _worksheet() -> gspread.Worksheet:
    settings = get_settings()
    gc = gspread.service_account(filename=settings.google_service_account_file)
    sheet = gc.open_by_key(settings.google_sheets_id)
    return sheet.worksheet(settings.google_sheets_worksheet)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip().lower()


def _digits(text: str) -> str:
    return "".join(c for c in str(text) if c.isdigit())


@_retry_google
def _column_map() -> dict[str, int]:
    """Mapeia campo lógico -> índice (1-based) da coluna, pelo cabeçalho real."""
    headers = _worksheet().row_values(1)
    mapping: dict[str, int] = {}
    for idx, header in enumerate(headers, start=1):
        h = _normalize(header)
        for field, keyword in COLUMN_KEYWORDS.items():
            if field not in mapping and keyword in h:
                mapping[field] = idx
    missing = set(COLUMN_KEYWORDS) - set(mapping)
    if missing:
        raise ValueError(
            f"Colunas não encontradas na planilha: {sorted(missing)}. "
            f"Cabeçalho atual: {headers}"
        )
    return mapping


@_retry_google
def _find_row_by_whatsapp(whatsapp_e164: str, col_map: dict[str, int]) -> int | None:
    """Localiza a linha do lead pela coluna whatsapp (comparação por dígitos)."""
    valores = _worksheet().col_values(col_map["whatsapp"])
    alvo = _digits(whatsapp_e164)
    for idx, valor in enumerate(valores[1:], start=2):  # pula o cabeçalho
        if _digits(valor) == alvo and alvo:
            return idx
    return None


@_retry_google
def upsert_curadoria_row(lead: dict, linkedin_url: str, funcionarios: str) -> None:
    """Grava (ou atualiza) a linha de curadoria do lead na planilha."""
    ws = _worksheet()
    col_map = _column_map()

    valores = {
        "nome": lead["nome"],
        "linkedin": linkedin_url,
        "whatsapp": lead["telefone_e164"],
        "empresa": lead["empresa"],
        "funcionarios": funcionarios,
        "validado": "não",
        # cargo fica em branco: é o campo do curador humano
    }

    row_idx = _find_row_by_whatsapp(lead["telefone_e164"], col_map)
    if row_idx is None:
        num_cols = max(col_map.values())
        nova_linha = [""] * num_cols
        for campo, valor in valores.items():
            nova_linha[col_map[campo] - 1] = valor
        ws.append_row(nova_linha, value_input_option="USER_ENTERED")
    else:
        # Atualiza sem sobrescrever o que é do humano (cargo/validado)
        for campo in ("nome", "linkedin", "whatsapp", "empresa", "funcionarios"):
            ws.update_cell(row_idx, col_map[campo], valores[campo])


@_retry_google
def read_validation(whatsapp_e164: str) -> dict:
    """Lê o estado de validação do lead na planilha (para watcher e tool)."""
    col_map = _column_map()
    row_idx = _find_row_by_whatsapp(whatsapp_e164, col_map)
    if row_idx is None:
        return {"encontrado": False, "validado": False, "cargo": None}

    row = _worksheet().row_values(row_idx)

    def _cell(campo: str) -> str:
        idx = col_map[campo] - 1
        return row[idx].strip() if idx < len(row) else ""

    return {
        "encontrado": True,
        "validado": _normalize(_cell("validado")) in ("sim", "s", "yes", "true"),
        "cargo": _cell("cargo") or None,
        "linkedin": _cell("linkedin") or None,
    }


# =============================================================================
# Tools do agente
# =============================================================================

class RegistrarCuradoriaArgs(BaseModel):
    linkedin_url: str = Field(description="URL do perfil do LinkedIn informada pelo lead.")
    funcionarios: str = Field(
        description=(
            "Quantidade de funcionários da empresa dita pelo lead "
            "(ex.: '850' ou 'entre 200 e 500')."
        )
    )


def make_registrar_curadoria_tool(lead: dict) -> StructuredTool:
    """Tool que grava a linha de curadoria e move o lead para validação humana."""

    def _registrar(linkedin_url: str, funcionarios: str) -> str:
        from core.supabase_client import get_supabase

        try:
            upsert_curadoria_row(lead, linkedin_url, funcionarios)
        except FileNotFoundError:
            return json.dumps(
                {"erro": "Credencial do Google não configurada; avise que a curadoria registrará manualmente."},
                ensure_ascii=False,
            )
        except (gspread.exceptions.APIError, ValueError) as exc:
            logger.warning("Falha ao gravar curadoria no Sheets: %s", exc)
            return json.dumps(
                {"erro": "Planilha de curadoria indisponível no momento."},
                ensure_ascii=False,
            )

        supabase = get_supabase()
        supabase.table("leads").update(
            {
                "linkedin_url": linkedin_url,
                "funcionarios": funcionarios,
                "status": "aguardando_validacao",
                "motivo_status": "LinkedIn enviado; aguardando curadoria humana",
            }
        ).eq("id", lead["id"]).execute()
        supabase.table("agent_events").insert(
            {
                "lead_id": lead["id"],
                "event_type": "curadoria_registrada",
                "payload": {"linkedin_url": linkedin_url, "funcionarios": funcionarios},
            }
        ).execute()

        return json.dumps(
            {"status": "registrado", "detalhe": "Lead enviado para a curadoria humana."},
            ensure_ascii=False,
        )

    return StructuredTool.from_function(
        func=_registrar,
        name="registrar_lead_curadoria",
        description=(
            "Registra este lead na planilha da curadoria humana. Use assim que "
            "tiver o link do LinkedIn E a quantidade de funcionários da empresa. "
            "Isso move o lead para a fila de validação."
        ),
        args_schema=RegistrarCuradoriaArgs,
    )


def make_sheets_tool(lead: dict) -> StructuredTool:
    """Tool de CONSULTA ao estado da curadoria (quando o lead pergunta)."""

    def _consultar() -> str:
        try:
            resultado = read_validation(lead["telefone_e164"])
        except FileNotFoundError:
            return json.dumps(
                {"erro": "Credencial do Google não configurada; validação indisponível."},
                ensure_ascii=False,
            )
        except (gspread.exceptions.APIError, ValueError) as exc:
            logger.warning("Google Sheets indisponível: %s", exc)
            return json.dumps(
                {"erro": "Planilha temporariamente indisponível. Tente mais tarde."},
                ensure_ascii=False,
            )

        if not resultado["encontrado"]:
            return json.dumps(
                {"status": "pendente", "detalhe": "Lead ainda não registrado na curadoria."},
                ensure_ascii=False,
            )
        return json.dumps({"status": "registrado", **resultado}, ensure_ascii=False)

    return StructuredTool.from_function(
        func=_consultar,
        name="consultar_validacao_linkedin",
        description=(
            "Consulta se a curadoria humana já validou o LinkedIn deste lead. "
            "Não recebe argumentos. Retorna JSON com validado (true/false) e o "
            "cargo confirmado pelo curador (se preenchido)."
        ),
    )