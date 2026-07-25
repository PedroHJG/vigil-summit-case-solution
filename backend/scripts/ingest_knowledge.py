"""Reindexa a base de conhecimento do evento no pgvector (Supabase).

Uso (a partir de /backend, com .env configurado e a migration 0004 aplicada):
    python -m scripts.ingest_knowledge

Rode sempre que editar backend/knowledge/vigil_summit_kb.md. É idempotente:
apaga e reinsere todos os chunks numa transação.
"""

import sys

sys.path.insert(0, ".")

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services import knowledge_service  # noqa: E402


def main() -> None:
    print(f"Lendo {knowledge_service.KB_PATH} ...")
    n = knowledge_service.ingest()
    print(f"OK! {n} chunks indexados no pgvector (tabela event_knowledge).")


if __name__ == "__main__":
    main()