"""Gráficos modulares (Plotly) do dashboard."""

import pandas as pd
import plotly.graph_objects as go

from components.data import STATUS_LABELS, STATUS_ORDER
from components.scoring import TEMP_ORDER
from components.theme import (
    FUNNEL_RAMP,
    FUNNEL_TEXT,
    INK_PRIMARY,
    INK_SECONDARY,
    SERIES_BLUE,
    SURFACE,
    TEMP_COLORS,
    base_layout,
)


def funnel_chart(funnel_df: pd.DataFrame) -> go.Figure:
    """Funil cumulativo em 5 etapas (rampa ordinal azul validada)."""
    fig = go.Figure(
        go.Funnel(
            y=funnel_df["etapa"],
            x=funnel_df["total"],
            marker={"color": FUNNEL_RAMP, "line": {"color": SURFACE, "width": 2}},
            connector={"line": {"color": SURFACE, "width": 2}},
            textinfo="value+percent initial",
            textfont={"color": FUNNEL_TEXT, "size": 13},
            hovertemplate="<b>%{y}</b><br>%{x} leads<extra></extra>",
        )
    )
    fig.update_layout(base_layout(height=360))
    return fig


def leads_por_dia(df: pd.DataFrame) -> go.Figure:
    """Série temporal de inscrições (série única: linha 2px, sem legenda)."""
    fig = go.Figure()
    if not df.empty:
        por_dia = (
            df.set_index("created_at")
            .resample("D")
            .size()
            .rename("total")
            .reset_index()
        )
        fig.add_trace(
            go.Scatter(
                x=por_dia["created_at"],
                y=por_dia["total"],
                mode="lines+markers",
                line={"color": SERIES_BLUE, "width": 2},
                marker={"size": 8, "color": SERIES_BLUE,
                        "line": {"color": SURFACE, "width": 2}},
                hovertemplate="%{x|%d/%m}<br><b>%{y}</b> inscrições<extra></extra>",
            )
        )
    fig.update_layout(base_layout(height=280))
    fig.update_yaxes(rangemode="tozero", dtick=1)
    return fig


def leads_por_cargo(df: pd.DataFrame) -> go.Figure:
    """Barras por cargo (uma medida, uma cor — identidade fica no eixo)."""
    fig = go.Figure()
    if not df.empty:
        por_cargo = df["cargo"].value_counts()
        fig.add_trace(
            go.Bar(
                x=por_cargo.values,
                y=por_cargo.index,
                orientation="h",
                marker={"color": SERIES_BLUE,
                        "line": {"color": SURFACE, "width": 2}},
                text=por_cargo.values,
                textposition="outside",
                textfont={"color": INK_PRIMARY},
                hovertemplate="<b>%{y}</b>: %{x} leads<extra></extra>",
            )
        )
    fig.update_layout(base_layout(height=280))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(showgrid=True)
    return fig


def temperatura_chart(df: pd.DataFrame) -> go.Figure:
    """Leads por temperatura (rampa ordinal frio→quente + neutro p/ descartado)."""
    fig = go.Figure()
    if not df.empty:
        counts = df["temperatura"].value_counts()
        ordem = [t for t in TEMP_ORDER if t in counts.index]
        fig.add_trace(
            go.Bar(
                x=[int(counts[t]) for t in ordem],
                y=ordem,
                orientation="h",
                marker={
                    "color": [TEMP_COLORS[t] for t in ordem],
                    "line": {"color": SURFACE, "width": 2},
                },
                text=[int(counts[t]) for t in ordem],
                textposition="outside",
                textfont={"color": INK_PRIMARY},
                hovertemplate="<b>%{y}</b>: %{x} leads<extra></extra>",
            )
        )
    fig.update_layout(base_layout(height=230))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(showgrid=True)
    return fig


def prob_distribuicao(df: pd.DataFrame) -> go.Figure:
    """Distribuição da probabilidade de presença (histograma, uma medida, uma cor)."""
    fig = go.Figure()
    if not df.empty:
        ativos = df[df["temperatura"] != "Descartado"]
        bins = pd.cut(
            ativos["prob_presenca"],
            bins=[0, 20, 40, 60, 80, 100],
            labels=["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"],
            include_lowest=True,
        )
        counts = bins.value_counts().sort_index()
        fig.add_trace(
            go.Bar(
                x=list(counts.index.astype(str)),
                y=counts.values,
                marker={"color": SERIES_BLUE, "line": {"color": SURFACE, "width": 2}},
                text=counts.values,
                textposition="outside",
                textfont={"color": INK_PRIMARY},
                hovertemplate="Probabilidade %{x}<br><b>%{y}</b> leads<extra></extra>",
            )
        )
    fig.update_layout(base_layout(height=260))
    fig.update_yaxes(rangemode="tozero", dtick=1, showgrid=True)
    return fig


def cargo_temperatura(df: pd.DataFrame) -> go.Figure:
    """Cargo × temperatura (barras empilhadas; rampa ordinal carrega a temperatura)."""
    fig = go.Figure()
    if not df.empty:
        tabela = (
            df.groupby(["cargo", "temperatura"]).size().unstack(fill_value=0)
        )
        cargos = tabela.sum(axis=1).sort_values(ascending=True).index
        for temp in TEMP_ORDER:  # ordem fixa da rampa (nunca reordenar por valor)
            if temp not in tabela.columns:
                continue
            fig.add_trace(
                go.Bar(
                    x=tabela.loc[cargos, temp].values,
                    y=list(cargos),
                    name=temp,
                    orientation="h",
                    marker={
                        "color": TEMP_COLORS[temp],
                        "line": {"color": SURFACE, "width": 2},
                    },
                    hovertemplate=f"<b>%{{y}}</b> · {temp}: %{{x}} leads<extra></extra>",
                )
            )
    fig.update_layout(
        base_layout(
            height=280,
            barmode="stack",
            showlegend=True,
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "font": {"color": INK_SECONDARY},
            },
        )
    )
    fig.update_xaxes(showgrid=True)
    return fig


def status_detalhado(df: pd.DataFrame) -> go.Figure:
    """Distribuição por status granular (uma medida, uma cor)."""
    fig = go.Figure()
    if not df.empty:
        counts = df["status"].value_counts()
        ordered = [s for s in STATUS_ORDER if s in counts.index]
        fig.add_trace(
            go.Bar(
                x=[int(counts[s]) for s in ordered],
                y=[STATUS_LABELS[s] for s in ordered],
                orientation="h",
                marker={"color": SERIES_BLUE,
                        "line": {"color": SURFACE, "width": 2}},
                text=[int(counts[s]) for s in ordered],
                textposition="outside",
                textfont={"color": INK_PRIMARY},
                hovertemplate="<b>%{y}</b>: %{x} leads<extra></extra>",
            )
        )
    fig.update_layout(base_layout(height=380))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(showgrid=True)
    return fig
