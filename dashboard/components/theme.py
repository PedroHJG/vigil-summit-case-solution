"""Tema visual dos gráficos — modo escuro (alinhado à landing page).

Cores do sistema validado de dataviz (superfície escura #1a1a19):
- Série única: azul slot 1 dark (#3987e5).
- Rampas ordinais validadas por scripts/validate_palette.js em --mode dark
  --ordinal: monotônicas, ΔL visível entre passos e extremo próximo à
  superfície ≥ 2:1. No escuro, o passo MAIS ESCURO fica perto da superfície
  (menor ênfase) e o mais claro carrega o destaque.
"""

# Superfícies e tinta (modo escuro)
SURFACE = "#1a1a19"        # superfície dos gráficos
PAGE = "#0d0d0d"           # plano da página
INK_PRIMARY = "#ffffff"
INK_SECONDARY = "#c3c2b7"
INK_MUTED = "#898781"
GRIDLINE = "#2c2c2a"
BASELINE = "#383835"

# Acento de UI (roxo da landing) — nunca usado como cor de dados
ACCENT = "#b341f2"

# Série única (magnitude): azul categórico slot 1 (dark)
SERIES_BLUE = "#3987e5"

# Rampa ordinal do funil (6 etapas, validada p/ dark): 600/500/400/300/200/100
FUNNEL_RAMP = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
# Texto sobre cada etapa: claro nos passos escuros, escuro nos passos claros
FUNNEL_TEXT = ["#ffffff", "#ffffff", "#ffffff", "#0b0b0b", "#0b0b0b", "#0b0b0b"]

# Rampa ordinal de temperatura (3 etapas, validada p/ dark): frio -> quente
TEMP_COLORS = {
    "Frio": "#184f95",
    "Morno": "#3987e5",
    "Quente": "#9ec5f4",
    "Descartado": "#52514e",  # neutro recessivo (fora da rampa)
}

FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def base_layout(**overrides) -> dict:
    """Layout Plotly padrão: chrome recessivo, tinta em tokens de texto."""
    layout = {
        "paper_bgcolor": SURFACE,
        "plot_bgcolor": SURFACE,
        "font": {"family": FONT_FAMILY, "color": INK_SECONDARY, "size": 13},
        "margin": {"l": 8, "r": 8, "t": 8, "b": 8},
        "xaxis": {
            "gridcolor": GRIDLINE,
            "linecolor": BASELINE,
            "tickfont": {"color": INK_MUTED},
            "zeroline": False,
        },
        "yaxis": {
            "gridcolor": GRIDLINE,
            "linecolor": BASELINE,
            "tickfont": {"color": INK_MUTED},
            "zeroline": False,
        },
        "hoverlabel": {
            "bgcolor": "#242423",
            "bordercolor": BASELINE,
            "font": {"family": FONT_FAMILY, "color": INK_PRIMARY, "size": 13},
        },
        "showlegend": False,  # gráficos de série única: o título nomeia a série
    }
    layout.update(overrides)
    return layout