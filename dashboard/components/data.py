"""Acesso a dados do Supabase para o dashboard (leitura apenas)."""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

# Ordem canônica do funil (espelha o enum status_lead do banco)
STATUS_ORDER = [
    "novo", "enriquecendo", "enriquecido", "em_conversa", "aguardando_validacao",
    "qualificado", "desqualificado", "confirmado", "compareceu", "ausente",
    "em_follow_up", "reuniao_agendada", "perdido",
]

STATUS_LABELS = {
    "novo": "Novo",
    "enriquecendo": "Enriquecendo",
    "enriquecido": "Enriquecido",
    "em_conversa": "Em conversa",
    "aguardando_validacao": "Aguard. validação",
    "qualificado": "Qualificado",
    "desqualificado": "Desqualificado",
    "confirmado": "Confirmado",
    "compareceu": "Compareceu",
    "ausente": "Ausente",
    "em_follow_up": "Em follow-up",
    "reuniao_agendada": "Reunião agendada",
    "perdido": "Perdido",
}

# Funil cumulativo: cada etapa conta os leads que CHEGARAM até ela (ou além)
FUNNEL_STAGES = [
    ("Inscritos", set(STATUS_ORDER)),
    ("Em conversa", {
        "em_conversa", "aguardando_validacao", "qualificado", "confirmado",
        "compareceu", "ausente", "em_follow_up", "reuniao_agendada",
    }),
    ("Qualificados", {
        "qualificado", "confirmado", "compareceu", "ausente",
        "em_follow_up", "reuniao_agendada",
    }),
    ("Confirmados", {
        "confirmado", "compareceu", "ausente", "em_follow_up", "reuniao_agendada",
    }),
    ("Compareceram", {"compareceu", "em_follow_up", "reuniao_agendada"}),
    ("Reunião agendada", {"reuniao_agendada"}),
]


@st.cache_resource
def get_client() -> Client:
    # Aceita a URL com /rest/v1 embutido (o SDK adiciona esse caminho sozinho)
    url = os.environ["SUPABASE_URL"].rstrip("/").removesuffix("/rest/v1").rstrip("/")
    return create_client(url, os.environ["SUPABASE_SERVICE_KEY"])


@st.cache_data(ttl=15)
def load_leads() -> pd.DataFrame:
    rows = (
        get_client()
        .table("leads")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["updated_at"] = pd.to_datetime(df["updated_at"])
    return df


@st.cache_data(ttl=30)
def load_notifications() -> pd.DataFrame:
    rows = (
        get_client()
        .table("notifications")
        .select("tipo, canal, destinatario, status, scheduled_for, sent_at")
        .order("scheduled_for", desc=True)
        .limit(200)
        .execute()
        .data
    )
    return pd.DataFrame(rows)


@st.cache_data(ttl=30)
def load_meetings() -> pd.DataFrame:
    rows = (
        get_client()
        .table("meetings")
        .select("titulo, start_time, status, html_link, leads(nome, empresa)")
        .order("start_time")
        .execute()
        .data
    )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["lead"] = df["leads"].apply(
            lambda l: f"{l['nome']} ({l['empresa']})" if l else "—"
        )
        df = df.drop(columns=["leads"])
    return df


def funnel_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame({"etapa": [s for s, _ in FUNNEL_STAGES], "total": 0})
    return pd.DataFrame(
        {
            "etapa": [stage for stage, _ in FUNNEL_STAGES],
            "total": [int(df["status"].isin(statuses).sum()) for _, statuses in FUNNEL_STAGES],
        }
    )
