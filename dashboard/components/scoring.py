"""Scoring de leads para o dashboard (transparente e auditável).

Duas métricas derivadas dos dados do funil:

1. PROBABILIDADE DE PRESENÇA (0–100%): chance estimada de o lead comparecer.
   Base pelo estágio do funil + ajustes por aderência ao ICP:
     - cargo executivo (CISO/CTO) ...... +7 p.p. | Diretor/Gestor ....... +4 p.p.
     - empresa com 200+ funcionários ... +5 p.p.
     - lead_score do agente (0-100) .... até +15 p.p. (0,15 × score)
   Estados terminais são fixos: compareceu/pós-evento = 100, ausente = 0.

2. TEMPERATURA: leitura comercial da probabilidade.
     Quente ≥ 60% | Morno 35–59% | Frio < 35% | Descartado (perdido, ausente,
     desqualificado).
"""

import pandas as pd

# Base da probabilidade por estágio do funil (p.p.)
STATUS_BASE_PROB = {
    "novo": 10,
    "enriquecendo": 10,
    "enriquecido": 15,
    "em_conversa": 28,
    "aguardando_validacao": 40,
    "qualificado": 55,
    "confirmado": 80,
    # estados terminais / pós-evento
    "compareceu": 100,
    "em_follow_up": 100,
    "reuniao_agendada": 100,
    "ausente": 0,
    "desqualificado": 0,
    "perdido": 2,
}

TERMINAL = {"compareceu", "em_follow_up", "reuniao_agendada", "ausente", "desqualificado"}
DESCARTADO = {"desqualificado", "perdido", "ausente"}

CARGO_EXEC = {"CISO", "CTO"}
CARGO_GESTAO = {"Diretor de TI", "Gestor de Risco"}

TEMP_ORDER = ["Quente", "Morno", "Frio", "Descartado"]


def _parse_funcionarios(valor) -> int | None:
    """'850', 'entre 200 e 500', '1.200+' -> maior número encontrado."""
    import re

    if valor is None:
        return None
    numeros = re.findall(r"\d+", str(valor).replace(".", ""))
    return max(int(n) for n in numeros) if numeros else None


def prob_presenca(lead: pd.Series) -> float:
    status = lead.get("status", "novo")
    base = STATUS_BASE_PROB.get(status, 10)
    if status in TERMINAL:
        return float(base)

    prob = float(base)
    # NaN do pandas é truthy: normaliza antes do fallback cargo_validado -> cargo
    cargo = lead.get("cargo_validado")
    if cargo is None or pd.isna(cargo) or not str(cargo).strip():
        cargo = lead.get("cargo")
    cargo = "" if (cargo is None or pd.isna(cargo)) else str(cargo)
    if cargo in CARGO_EXEC:
        prob += 7
    elif cargo in CARGO_GESTAO:
        prob += 4

    func = _parse_funcionarios(lead.get("funcionarios"))
    if func is not None and func >= 200:
        prob += 5

    # Levar acompanhante é compromisso social com a própria presença
    acomp = lead.get("acompanhantes")
    if pd.notna(acomp) and acomp and int(acomp) >= 1:
        prob += 4

    score = lead.get("lead_score")
    if pd.notna(score) and score is not None:
        prob += 0.15 * float(score)

    return float(min(max(prob, 2), 95))


def temperatura(lead: pd.Series) -> str:
    if lead.get("status") in DESCARTADO:
        return "Descartado"
    p = lead["prob_presenca"]
    if p >= 60:
        return "Quente"
    if p >= 35:
        return "Morno"
    return "Frio"


def enrich_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona prob_presenca (%) e temperatura ao DataFrame de leads."""
    if df.empty:
        df = df.copy()
        df["prob_presenca"] = pd.Series(dtype=float)
        df["temperatura"] = pd.Series(dtype=str)
        return df

    out = df.copy()
    if "funcionarios" not in out.columns:
        out["funcionarios"] = None
    if "acompanhantes" not in out.columns:
        out["acompanhantes"] = 0
    out["acompanhantes"] = out["acompanhantes"].fillna(0).astype(int)
    out["prob_presenca"] = out.apply(prob_presenca, axis=1)
    out["temperatura"] = out.apply(temperatura, axis=1)
    return out


def presenca_esperada(df: pd.DataFrame) -> float:
    """Nº esperado de LEADS presentes (soma das probabilidades dos não descartados)."""
    if df.empty:
        return 0.0
    ativos = df[~df["status"].isin(DESCARTADO)]
    return float(ativos["prob_presenca"].sum() / 100)


def pessoas_esperadas(df: pd.DataFrame) -> float:
    """Nº esperado de PESSOAS (lead + acompanhantes; acompanhante só vai se o lead for)."""
    if df.empty:
        return 0.0
    ativos = df[~df["status"].isin(DESCARTADO)]
    return float(
        (ativos["prob_presenca"] / 100 * (1 + ativos["acompanhantes"])).sum()
    )