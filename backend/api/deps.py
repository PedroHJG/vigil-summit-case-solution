"""Dependências compartilhadas das rotas."""

from fastapi import Header, HTTPException, status

from core.config import get_settings


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Protege os endpoints internos chamados pelo n8n."""
    if x_api_key != get_settings().backend_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key inválida ou ausente.",
        )
