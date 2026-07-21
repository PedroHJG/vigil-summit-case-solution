"""Materializa credenciais do Google a partir de variáveis de ambiente.

Em hosts sem filesystem persistente versionável (Render, Railway, Fly...), os
arquivos de `backend/credentials/` (git-ignorados) não existem no deploy. Em
vez de depender de um recurso de "secret files" específico da plataforma
(cujas regras de nome variam e podem não aceitar caminhos com barra), o valor
bruto do JSON pode ser colado numa env var comum — sem restrição de caractere
no *valor* — e este módulo grava o arquivo esperado no boot, no MESMO caminho
já configurado em `GOOGLE_*_FILE`. Nenhum outro código (sheets.py, calendar.py)
precisa saber a diferença: eles sempre leem do caminho em disco.

Idempotente e silencioso quando as env vars não estão setadas (uso local,
onde os arquivos já existem em `credentials/`).
"""

import json
import logging
from pathlib import Path

from core.config import get_settings

logger = logging.getLogger(__name__)

# (env var com o JSON bruto, setting do caminho onde deve ser gravado)
_CREDENTIAL_VARS = [
    ("google_service_account_json", "google_service_account_file"),
    ("google_oauth_client_json", "google_oauth_client_file"),
    ("google_oauth_token_json", "google_oauth_token_file"),
]


def materialize_google_credentials() -> None:
    settings = get_settings()

    for json_field, path_field in _CREDENTIAL_VARS:
        raw = getattr(settings, json_field, "").strip()
        if not raw:
            continue

        try:
            json.loads(raw)  # valida antes de gravar; erro claro > arquivo corrompido
        except json.JSONDecodeError:
            logger.error(
                "%s não contém um JSON válido — credencial não foi gravada.",
                json_field.upper(),
            )
            continue

        target = Path(getattr(settings, path_field))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(raw, encoding="utf-8")
        logger.info("Credencial Google materializada em %s (via env var).", target)