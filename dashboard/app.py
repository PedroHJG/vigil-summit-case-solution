"""Vigil Summit — Dashboard de monitoramento do funil de leads (Streamlit).

Executar (a partir de /dashboard, com .env configurado):
    streamlit run app.py
"""

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components import dash_charts as charts
from components.data import (
    EVENT_CAPACITY,
    STATUS_COM_VAGA,
    STATUS_LABELS,
    funnel_counts,
    load_leads,
    load_meetings,
    load_notifications,
)
from components.scoring import (
    DESCARTADO,
    TEMP_ORDER,
    enrich_scores,
    pessoas_esperadas,
    presenca_esperada,
)

st.set_page_config(
    page_title="Vigil Summit — Funil de Leads",
    page_icon="🛡️",
    layout="wide",
)

# Ajustes visuais (tema escuro alinhado à landing): cartões com borda suave,
# acento roxo discreto e chrome do Streamlit escondido
st.markdown(
    """
    <style>
      [data-testid="stMetric"] {
        background: linear-gradient(160deg, rgba(179,65,242,0.08), rgba(57,135,229,0.05));
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 14px;
        padding: 14px 16px;
      }
      [data-testid="stMetricLabel"] { opacity: 0.78; }
      [data-testid="stMetricValue"] { font-weight: 600; }
      div[data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
      }
      h1, h2, h3 { letter-spacing: -0.01em; }
      hr { border-color: rgba(255,255,255,0.08); }
      #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

st_autorefresh(interval=15_000, key="auto_refresh")

st.title("🛡️ Vigil Summit — Funil de Leads")
st.caption("Monitoramento em tempo real · atualiza a cada 15s · fonte: Supabase")

try:
    leads_raw = load_leads()
except Exception as exc:
    st.error(f"Não foi possível conectar ao Supabase: {exc}")
    st.stop()

leads_all = enrich_scores(leads_raw)

# =============================================================================
# Filtros (uma linha, acima de tudo — aplicam a todo o dashboard)
# =============================================================================

f1, f2, f3, f4 = st.columns([1, 1, 1, 1.4])
with f1:
    cargos_sel = st.multiselect(
        "Cargo",
        options=sorted(leads_all["cargo"].dropna().unique()) if not leads_all.empty else [],
        placeholder="Todos",
    )
with f2:
    empresas_sel = st.multiselect(
        "Empresa",
        options=sorted(leads_all["empresa"].dropna().unique()) if not leads_all.empty else [],
        placeholder="Todas",
    )
with f3:
    temp_sel = st.multiselect("Temperatura", options=TEMP_ORDER, placeholder="Todas")
with f4:
    busca = st.text_input(
        "Buscar (nome, e-mail ou ID do lead)", placeholder="ex.: Pedro, @acme.com, c1a8a3e8…"
    )

leads = leads_all
if cargos_sel:
    leads = leads[leads["cargo"].isin(cargos_sel)]
if empresas_sel:
    leads = leads[leads["empresa"].isin(empresas_sel)]
if temp_sel:
    leads = leads[leads["temperatura"].isin(temp_sel)]
if busca.strip():
    q = busca.strip().lower()
    leads = leads[
        leads["nome"].str.lower().str.contains(q, na=False)
        | leads["email"].str.lower().str.contains(q, na=False)
        | leads["id"].astype(str).str.lower().str.contains(q, na=False)
    ]

if len(leads) != len(leads_all):
    st.caption(f"Filtros ativos — exibindo {len(leads)} de {len(leads_all)} leads.")

# =============================================================================
# KPIs ligados aos problemas de negócio
# =============================================================================

total = len(leads)
ativos = leads[~leads["status"].isin(DESCARTADO)] if total else leads
quentes = int((leads["temperatura"] == "Quente").sum()) if total else 0
qualificados = int(leads["status"].isin(
    ["qualificado", "confirmado", "compareceu", "em_follow_up", "reuniao_agendada"]
).sum()) if total else 0
confirmados = int(leads["status"].isin(
    ["confirmado", "compareceu", "em_follow_up", "reuniao_agendada"]
).sum()) if total else 0
reunioes = int((leads["status"] == "reuniao_agendada").sum()) if total else 0
esperados = presenca_esperada(leads)
pessoas = pessoas_esperadas(leads)
acompanhantes_total = int(leads.loc[
    leads["status"].isin(["confirmado", "compareceu", "em_follow_up", "reuniao_agendada"]),
    "acompanhantes",
].sum()) if total else 0

# Vagas: sempre sobre a base COMPLETA (capacidade é global, não afetada por filtro).
vagas_ocupadas = int(leads_all["status"].isin(STATUS_COM_VAGA).sum()) if len(leads_all) else 0
vagas_restantes = max(0, EVENT_CAPACITY - vagas_ocupadas)

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("Leads captados", total, help="Total de inscrições recebidas pela landing (após filtros).")
k2.metric(
    "Taxa de qualificação",
    f"{(qualificados / total * 100):.0f}%" if total else "—",
    f"{quentes} quentes",
    delta_color="off",
    help="Problema 1 — leads qualificados: % que passou da curadoria (qualificado ou além).",
)
k3.metric(
    "Confirmados",
    confirmados,
    f"{(confirmados / qualificados * 100):.0f}% dos qualificados" if qualificados else None,
    delta_color="off",
    help="Problema 2 — no-show: inscrições confirmadas via botão do WhatsApp. Meta: comparecimento > 70%.",
)
k4.metric(
    "Acompanhantes",
    acompanhantes_total,
    help="Convidados extras registrados pelos confirmados (máx. 2 por lead) — alavanca anti no-show da régua D-7.",
)
k5.metric(
    "Pessoas esperadas",
    f"≈ {pessoas:.0f}",
    f"{esperados:.0f} leads + acompanhantes",
    delta_color="off",
    help="Projeção de público: probabilidade de presença × (1 + acompanhantes) de cada lead ativo.",
)
k6.metric(
    "Reuniões agendadas",
    reunioes,
    help="Problema 3 — follow-up: conversões em reunião comercial pós-evento.",
)
k7.metric(
    "Vagas",
    f"{vagas_ocupadas}/{EVENT_CAPACITY}",
    f"{vagas_restantes} restantes" if vagas_restantes else "ESGOTADO",
    delta_color="off",
    help="Capacidade do evento (120 lugares). Ao esgotar, novas confirmações são "
         "bloqueadas (FCFS) e interações de não-confirmados recebem aviso.",
)

st.divider()

# =============================================================================
# Funil + temperatura
# =============================================================================

c_funil, c_temp = st.columns([1.25, 1])
with c_funil:
    st.subheader("Funil do evento")
    st.plotly_chart(
        charts.funnel_chart(funnel_counts(leads)),
        use_container_width=True,
        config={"displayModeBar": False},
    )
with c_temp:
    st.subheader("Temperatura dos leads")
    st.plotly_chart(
        charts.temperatura_chart(leads),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.subheader("Probabilidade de presença")
    st.plotly_chart(
        charts.prob_distribuicao(leads),
        use_container_width=True,
        config={"displayModeBar": False},
    )

with st.expander("Como a probabilidade e a temperatura são calculadas"):
    st.markdown(
        """
        **Probabilidade de presença** parte do estágio do funil (novo 10% → em conversa 28%
        → aguardando validação 40% → qualificado 55% → confirmado 80%) e soma aderência ao
        ICP: cargo executivo (CISO/CTO) **+7 p.p.**, Diretor/Gestor **+4 p.p.**, empresa 200+
        funcionários **+5 p.p.**, acompanhante registrado **+4 p.p.** (compromisso social),
        **aderência do setor ±6 p.p.** (setor tech/regulado sobe, varejo desce) e até
        **+15 p.p.** pelo score dado pelo agente na conversa.
        Compareceu/pós-evento = 100%; ausente = 0%.

        **Temperatura**: 🔥 Quente ≥ 60% · Morno 35–59% · Frio < 35% · Descartado
        (desqualificado, perdido ou ausente).
        """
    )

# =============================================================================
# Perfil da base + evolução
# =============================================================================

c_cargo, c_dia = st.columns(2)
with c_cargo:
    st.subheader("Cargo × temperatura")
    st.plotly_chart(
        charts.cargo_temperatura(leads),
        use_container_width=True,
        config={"displayModeBar": False},
    )
with c_dia:
    st.subheader("Inscrições por dia")
    st.plotly_chart(
        charts.leads_por_dia(leads),
        use_container_width=True,
        config={"displayModeBar": False},
    )

# =============================================================================
# Detalhamento
# =============================================================================

tab_leads, tab_status, tab_notif, tab_meet = st.tabs(
    ["🎯 Leads priorizados", "Status detalhado", "Notificações", "Reuniões"]
)

with tab_leads:
    if leads.empty:
        st.info("Nenhum lead com os filtros atuais.")
    else:
        tabela = leads.sort_values("prob_presenca", ascending=False).copy()
        tabela["status"] = tabela["status"].map(STATUS_LABELS).fillna(tabela["status"])
        tabela["cargo_final"] = tabela["cargo_validado"].fillna(tabela["cargo"])
        if "setor_score" not in tabela.columns:
            tabela["setor_score"] = None
        st.dataframe(
            tabela[
                ["nome", "empresa", "cargo_final", "funcionarios", "setor_score",
                 "acompanhantes", "temperatura", "prob_presenca", "status",
                 "lead_score", "email", "id"]
            ].rename(columns={
                "nome": "Nome", "empresa": "Empresa", "cargo_final": "Cargo",
                "funcionarios": "Funcionários", "setor_score": "Aderência setor",
                "acompanhantes": "Acompanhantes", "temperatura": "Temperatura",
                "prob_presenca": "Prob. presença", "status": "Status",
                "lead_score": "Score agente", "email": "E-mail", "id": "ID",
            }),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prob. presença": st.column_config.ProgressColumn(
                    format="%.0f%%", min_value=0, max_value=100
                ),
                "Aderência setor": st.column_config.ProgressColumn(
                    format="%d", min_value=0, max_value=100,
                    help="Aderência do setor da empresa ao ICP (Claude, 0-100).",
                ),
                "Score agente": st.column_config.NumberColumn(format="%d"),
            },
        )

with tab_status:
    st.plotly_chart(
        charts.status_detalhado(leads),
        use_container_width=True,
        config={"displayModeBar": False},
    )

with tab_notif:
    notifs = load_notifications()
    if notifs.empty:
        st.info("Nenhuma notificação agendada.")
    else:
        resumo = notifs["status"].value_counts()
        n1, n2, n3 = st.columns(3)
        n1.metric("Agendadas", int(resumo.get("agendada", 0)))
        n2.metric("Enviadas", int(resumo.get("enviada", 0)))
        n3.metric("Falhas", int(resumo.get("falha", 0)))
        st.dataframe(notifs, use_container_width=True, hide_index=True)

with tab_meet:
    meetings = load_meetings()
    if meetings.empty:
        st.info("Nenhuma reunião agendada ainda.")
    else:
        st.dataframe(
            meetings[["lead", "titulo", "start_time", "status", "html_link"]].rename(
                columns={
                    "lead": "Lead", "titulo": "Título", "start_time": "Início",
                    "status": "Status", "html_link": "Link",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={"Link": st.column_config.LinkColumn()},
        )