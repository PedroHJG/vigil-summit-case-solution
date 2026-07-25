"""Enriquecimento do lead: scraping do site da empresa + resumo estruturado (Claude).

Falha de scraping NÃO bloqueia o funil: o lead segue para engajamento com
contexto vazio e o erro fica registrado em lead_enrichment.
"""

import json
import logging
from datetime import datetime, timezone

from agent.chains import build_enrichment_summary_chain
from agent.tools.scraper import scrape_site
from api.schemas import EnrichmentResult
from core.supabase_client import get_supabase
from services import lead_service

logger = logging.getLogger(__name__)


def _clamp_score(valor) -> int | None:
    """Normaliza o setor_aderencia do LLM para um inteiro 0-100 (ou None)."""
    try:
        return max(0, min(100, int(round(float(valor)))))
    except (TypeError, ValueError):
        return None


def enrich_lead(lead_id: str) -> EnrichmentResult:
    supabase = get_supabase()
    lead = lead_service.get_lead(lead_id)

    # Lock otimista: tira o lead de 'novo' imediatamente para o polling do n8n
    # não reprocessá-lo no próximo ciclo.
    lead_service.update_status(lead_id, "enriquecendo")

    dominio = lead.get("dominio_empresa") or lead_service.domain_from_email(lead["email"])
    scraped = scrape_site(dominio)

    summary = industry = size_hint = None
    security_context = None
    setor_score = None
    enrich_status = "falha"

    if scraped["content"]:
        try:
            chain = build_enrichment_summary_chain()
            parsed = chain.invoke(
                {
                    "empresa": lead["empresa"],
                    "website_url": scraped["website_url"] or dominio,
                    "conteudo": scraped["content"],
                }
            )
            summary = parsed.get("summary")
            industry = parsed.get("industry")
            size_hint = parsed.get("company_size_hint")
            security_context = {"ganchos": parsed.get("ganchos", [])}
            setor_score = _clamp_score(parsed.get("setor_aderencia"))
            enrich_status = "sucesso"
        except Exception as exc:
            logger.exception("Falha ao resumir conteúdo do lead %s", lead_id)
            scraped["error"] = f"Scraping ok, mas o resumo falhou: {exc}"

    supabase.table("lead_enrichment").upsert(
        {
            "lead_id": lead_id,
            "website_url": scraped["website_url"],
            "pages_scraped": scraped["pages_scraped"],
            "raw_content": scraped["content"][:20000] if scraped["content"] else None,
            "summary": summary,
            "industry": industry,
            "company_size_hint": size_hint,
            "security_context": security_context,
            "status": enrich_status,
            "error": scraped["error"],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="lead_id",
    ).execute()

    # setor_score vive em `leads` (o scoring do dashboard e a validação de ICP
    # leem dessa tabela). Só grava quando o LLM classificou de fato.
    if setor_score is not None:
        supabase.table("leads").update({"setor_score": setor_score}).eq(
            "id", lead_id
        ).execute()

    lead_service.update_status(lead_id, "enriquecido")
    lead_service.log_event(
        lead_id,
        "enriquecimento",
        {"status": enrich_status, "paginas": len(scraped["pages_scraped"]),
         "setor_score": setor_score},
    )

    return EnrichmentResult(
        lead_id=lead_id,
        status=enrich_status,
        website_url=scraped["website_url"],
        pages_scraped=scraped["pages_scraped"],
        summary=summary,
        industry=industry,
        company_size_hint=size_hint,
        error=scraped["error"],
    )


def get_enrichment_context(lead_id: str) -> str:
    """Monta o bloco de contexto usado nos system prompts dos agentes."""
    supabase = get_supabase()
    result = (
        supabase.table("lead_enrichment").select("*").eq("lead_id", lead_id).execute()
    )
    if not result.data:
        return ""

    e = result.data[0]
    partes = []
    if e.get("summary"):
        partes.append(f"Resumo: {e['summary']}")
    if e.get("industry"):
        partes.append(f"Setor: {e['industry']}")
    if e.get("company_size_hint"):
        partes.append(f"Porte: {e['company_size_hint']}")
    ganchos = (e.get("security_context") or {}).get("ganchos") or []
    if ganchos:
        partes.append("Ganchos de conversa: " + "; ".join(ganchos))
    if e.get("website_url"):
        partes.append(f"Site: {e['website_url']}")
    return "\n".join(partes)
