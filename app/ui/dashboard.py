import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from app.services.counts_repository import CountsRepository
from app.services.dashboard_reporting import build_insight, compute_kpis, generate_pdf_report


st.set_page_config(
    page_title="PeopleFlowMonitor | Business Intelligence",
    page_icon="📊",
    layout="wide",
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
DB_PATH = os.path.join(ROOT_DIR, "data", "PeopleFlowMonitor.db")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)
COUNTS_REPO = CountsRepository(DB_PATH)


def get_data(start_dt: datetime, end_dt: datetime):
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(columns=["direction", "timestamp"]), "Arquivo nao encontrado"

    try:
        df = COUNTS_REPO.fetch_counts_between(start_dt, end_dt)
        if df.empty:
            return df, "Banco vazio"

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        df["data_referencia"] = df["timestamp"].dt.date
        return df, "Conectado"
    except Exception as e:
        return pd.DataFrame(columns=["direction", "timestamp"]), f"Erro: {str(e)}"


def render_kpi_block(df_filtered, ativar_limite: bool, limit_val):
    kpis = compute_kpis(df_filtered)
    in_total = kpis["in_total"]
    out_total = kpis["out_total"]
    current_occ = kpis["occupancy"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entradas Totais", f"{in_total}")
    c2.metric("Saidas Totais", f"{out_total}")

    if ativar_limite and current_occ >= limit_val:
        st.error(f"**CAPACIDADE MAXIMA ATINGIDA** ({current_occ}/{limit_val})")
        c3.metric("Ocupacao Critica", f"{current_occ}", delta="LIMITE!")
    elif ativar_limite and current_occ >= limit_val * 0.8:
        st.warning("**CAPACIDADE EM NIVEL DE ATENCAO**")
        c3.metric("Ocupacao Atual", f"{current_occ}", delta="80%+")
    else:
        delta_msg = f"Limite: {limit_val}" if ativar_limite else "Livre"
        c3.metric("Ocupacao Atual", f"{current_occ}", delta=delta_msg)

    c4.metric("Media Mov./Hora", f"{kpis['avg_h']}")


st.sidebar.title("Filtros e BI")
date_selected = st.sidebar.date_input("Data da Analise", datetime.now().date())
ativar_limite = st.sidebar.toggle("Habilitar Controle de Capacidade", value=False)
limit_val = st.sidebar.number_input("Limite de Pessoas", min_value=1, value=50) if ativar_limite else None
live_kpi_interval = 5

period_start = datetime.combine(date_selected, datetime.min.time())
period_end = period_start + timedelta(days=1)

if st.sidebar.button("Gerar Relatorio Executivo"):
    df_all, _ = get_data(period_start, period_end)
    df_f = df_all[df_all["data_referencia"] == date_selected].copy()
    if not df_f.empty:
        df_f["Hora"] = df_f["timestamp"].dt.hour
        chart_data = df_f.groupby(["Hora", "direction"]).size().reset_index(name="Qtde")
        fig_pdf = px.bar(
            chart_data,
            x="Hora",
            y="Qtde",
            color="direction",
            barmode="group",
            color_discrete_map={"IN": "#18345A", "OUT": "#A4B0BE"},
            template="plotly_white",
        )
        with st.spinner("Construindo documento..."):
            try:
                res = generate_pdf_report(df_f, date_selected, fig_pdf, limit_val, DOCS_DIR)
                if res:
                    st.sidebar.success("Relatorio Pronto")
            except Exception as e:
                st.sidebar.error(f"Erro no PDF: {e}")
    else:
        st.sidebar.warning("Sem dados para esta data.")


st.title("📊 PeopleFlowMonitor")
st.markdown(f"Painel de BI - Data: **{date_selected.strftime('%d/%m/%Y')}**")

df_all, status = get_data(period_start, period_end)

if not df_all.empty:
    df_filtered = df_all.copy()
    st.info(build_insight(df_filtered))

    if not df_filtered.empty:
        if hasattr(st, "fragment"):
            @st.fragment(run_every=f"{int(live_kpi_interval)}s")
            def _live_kpis():
                fresh_df_all, _ = get_data(period_start, period_end)
                fresh_df_filtered = fresh_df_all
                if fresh_df_filtered.empty:
                    st.info("Sem novos registros para atualizar KPIs.")
                    return
                render_kpi_block(fresh_df_filtered, ativar_limite, limit_val)

            _live_kpis()
        else:
            render_kpi_block(df_filtered, ativar_limite, limit_val)

        st.markdown("---")

        df_filtered["Hora"] = df_filtered["timestamp"].dt.hour
        chart_data = df_filtered.groupby(["Hora", "direction"]).size().reset_index(name="Quantidade")
        fig = px.bar(
            chart_data,
            x="Hora",
            y="Quantidade",
            color="direction",
            barmode="group",
            title="Mapa de Atividade por Faixa Horaria",
            color_discrete_map={"IN": "#18345A", "OUT": "#A4B0BE"},
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Logs Brutos do Banco de Dados"):
            st.dataframe(df_filtered.sort_values("timestamp", ascending=False), use_container_width=True)
    else:
        st.info(f"Nenhum registro encontrado para {date_selected.strftime('%d/%m/%Y')}.")
else:
    st.warning(f"Status da Conexao: {status}")
