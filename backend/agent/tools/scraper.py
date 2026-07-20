"""Tool de web scraping (enriquecimento do lead).

Estratégia:
1. O domínio da empresa é derivado do e-mail corporativo do lead
   (ex.: joao@acme.com.br -> acme.com.br).
2. Tenta resolver o site (https://dominio, https://www.dominio).
3. Baixa a home + páginas institucionais candidatas (/sobre, /about, ...),
   respeitando timeout, limite de páginas e limite de caracteres.
4. Extrai texto limpo (título, meta description, headings, parágrafos).

`scrape_site()` é a função pura reutilizada pelo EnrichmentService;
`scrape_company_website` é a Tool LangChain equivalente, disponível para
qualquer agente que precise de contexto sob demanda.
"""

import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import get_settings

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; VigilSummitBot/1.0; +https://vigilsummit.example/bot)"
)

# Páginas institucionais com maior densidade de contexto comercial
CANDIDATE_PATHS = [
    "/sobre", "/sobre-nos", "/quem-somos", "/about", "/about-us",
    "/empresa", "/institucional", "/produtos", "/solucoes", "/services",
]

_RETRYABLE = (httpx.TimeoutException, httpx.TransportError)


@retry(
    retry=retry_if_exception_type(_RETRYABLE),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _fetch(client: httpx.Client, url: str) -> httpx.Response:
    return client.get(url)


def _extract_text(html: str, max_chars: int) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()

    parts: list[str] = []

    if soup.title and soup.title.string:
        parts.append(f"TÍTULO: {soup.title.string.strip()}")

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        parts.append(f"DESCRIÇÃO: {meta['content'].strip()}")

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(" ", strip=True)
        if len(text) >= 30:
            parts.append(text)

    seen: set[str] = set()
    unique = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return "\n".join(unique)[:max_chars]


def resolve_website(dominio_ou_url: str, client: httpx.Client) -> str | None:
    """Descobre a URL base acessível a partir de um domínio ou URL."""
    value = dominio_ou_url.strip().lower()
    if value.startswith(("http://", "https://")):
        candidates = [value]
    else:
        candidates = [f"https://{value}", f"https://www.{value}", f"http://{value}"]

    for url in candidates:
        try:
            resp = _fetch(client, url)
            if resp.status_code < 400:
                return str(resp.url)
        except httpx.HTTPError:
            continue
    return None


def scrape_site(dominio_ou_url: str) -> dict:
    """Coleta o conteúdo institucional do site da empresa.

    Retorna: {"website_url", "pages_scraped": [...], "content", "error"}.
    Nunca levanta exceção — falhas são reportadas no campo "error" para que o
    fluxo de engajamento continue mesmo sem enriquecimento.
    """
    settings = get_settings()
    result: dict = {
        "website_url": None,
        "pages_scraped": [],
        "content": "",
        "error": None,
    }

    try:
        with httpx.Client(
            timeout=settings.scraper_timeout_seconds,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
            follow_redirects=True,
        ) as client:
            base_url = resolve_website(dominio_ou_url, client)
            if not base_url:
                result["error"] = f"Site inacessível para '{dominio_ou_url}'."
                return result

            result["website_url"] = base_url
            chunks: list[str] = []
            budget = settings.scraper_max_chars

            urls = [base_url] + [urljoin(base_url, p) for p in CANDIDATE_PATHS]
            visited: set[str] = set()

            for url in urls:
                if len(result["pages_scraped"]) >= settings.scraper_max_pages or budget <= 0:
                    break
                normalized = urlparse(url)._replace(fragment="").geturl().rstrip("/")
                if normalized in visited:
                    continue
                visited.add(normalized)

                try:
                    resp = _fetch(client, url)
                except httpx.HTTPError:
                    continue
                if resp.status_code >= 400:
                    continue
                if "text/html" not in resp.headers.get("content-type", ""):
                    continue

                text = _extract_text(resp.text, max_chars=budget)
                if not text:
                    continue

                chunks.append(f"===== PÁGINA: {url} =====\n{text}")
                budget -= len(text)
                result["pages_scraped"].append(url)

            result["content"] = "\n\n".join(chunks)
            if not result["content"]:
                result["error"] = "Nenhum conteúdo textual relevante encontrado."
    except Exception as exc:  # rede/parsing imprevisível: falha nunca derruba o fluxo
        logger.exception("Falha inesperada no scraping de %s", dominio_ou_url)
        result["error"] = str(exc)

    return result


@tool("scrape_company_website")
def scrape_company_website(dominio_ou_url: str) -> str:
    """Extrai o conteúdo institucional do site de uma empresa.

    Use quando precisar de contexto sobre a empresa de um lead (o que ela faz,
    setor, produtos). Informe o domínio (ex.: "acme.com.br") ou a URL completa.
    Retorna o texto extraído das páginas institucionais ou uma mensagem de erro.
    """
    result = scrape_site(dominio_ou_url)
    if result["error"] and not result["content"]:
        return f"ERRO: {result['error']}"
    return result["content"]
