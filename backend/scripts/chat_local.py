"""Chat local com o agente (sem WhatsApp) — útil para testar prompts e tools.

Uso (a partir de /backend, com .env configurado e um lead existente):
    python -m scripts.chat_local <lead_id> [pre|pos]

Simula a conversa no terminal usando a MESMA chain e memória do fluxo real.
"""

import sys

sys.path.insert(0, ".")

from agent.chains import (  # noqa: E402
    build_post_event_chain,
    build_pre_event_chain,
    extract_output_text,
)
from agent.prompts import KICKOFF_POST_EVENT, KICKOFF_PRE_EVENT  # noqa: E402
from services import enrichment_service, lead_service  # noqa: E402
from services.agent_service import _get_or_create_conversation  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.chat_local <lead_id> [pre|pos]")
        raise SystemExit(1)

    lead_id = sys.argv[1]
    fase = "pos_evento" if (len(sys.argv) > 2 and sys.argv[2] == "pos") else "pre_evento"

    lead = lead_service.get_lead(lead_id)
    contexto = enrichment_service.get_enrichment_context(lead_id)
    conversation = _get_or_create_conversation(lead_id, fase)
    session_id = str(conversation["session_id"])

    chain = (
        build_post_event_chain(lead, contexto)
        if fase == "pos_evento"
        else build_pre_event_chain(lead, contexto)
    )
    config = {"configurable": {"session_id": session_id}}

    print(f"\n=== Chat local | lead: {lead['nome']} | fase: {fase} ===")
    print("(digite 'sair' para encerrar; 'kickoff' dispara a 1a mensagem)\n")

    while True:
        user_input = input("Você (lead): ").strip()
        if user_input.lower() in ("sair", "exit", "quit"):
            break
        if user_input.lower() == "kickoff":
            user_input = KICKOFF_POST_EVENT if fase == "pos_evento" else KICKOFF_PRE_EVENT

        result = chain.invoke({"input": user_input}, config=config)
        print(f"\nSofia: {extract_output_text(result)}\n")


if __name__ == "__main__":
    main()
