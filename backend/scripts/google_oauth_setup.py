"""Autoriza a conta Google do DONO da agenda (one-time setup).

Por que: com OAuth do dono, o backend consegue (1) convidar o lead para os
eventos — o convite entra na agenda dele automaticamente — e (2) ler o
free/busy real da agenda do dono para propor horários de reunião.

Passos:
1. No Google Cloud Console (mesmo projeto das APIs): APIs & Services >
   Credentials > Create Credentials > OAuth client ID > tipo "Desktop app".
   Baixe o JSON como backend/credentials/oauth_client.json.
   (Em "OAuth consent screen", adicione seu e-mail como test user.)
2. Rode (a partir de /backend):  python -m scripts.google_oauth_setup
3. Faça login no navegador com a conta dona da agenda e autorize.

O token (com refresh_token) fica em backend/credentials/google_oauth_token.json
e é renovado automaticamente pelo backend.
"""

import sys
from pathlib import Path

sys.path.insert(0, ".")

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from core.config import get_settings  # noqa: E402

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main() -> None:
    settings = get_settings()
    client_file = Path(settings.google_oauth_client_file)
    if not client_file.exists():
        print(f"ERRO: {client_file} não encontrado.")
        print("Crie um OAuth client ID (tipo Desktop app) no Google Cloud Console e")
        print(f"salve o JSON em {client_file}.")
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    token_file = Path(settings.google_oauth_token_file)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    print(f"OK! Token salvo em {token_file}.")
    print("O backend passará a usar a conta autorizada para o Google Calendar.")


if __name__ == "__main__":
    main()