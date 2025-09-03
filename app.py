# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import run_query

st.set_page_config(page_title="Análise de Alunos", page_icon="🎓", layout="wide")

st.title("📊 Alunos por Série")

# --- SQL fixa (conforme solicitado) ---
SQL = """
SELECT 
    serie AS categoria,
    COUNT(DISTINCT id) AS qtd_alunos
FROM dbo.tb_alunos
GROUP BY serie
ORDER BY qtd_alunos DESC;
"""

with st.expander("🔎 SQL gerada"):
    st.code(SQL, language="sql")

# --- Consultar ---
with st.spinner("Consultando o Lakehouse..."):
    try:
        df = run_query(SQL)
    except Exception as e:
        st.error(f"Erro ao consultar o SQL endpoint: {e}")
        st.stop()

# --- Exibir ---
if df.empty:
    st.warning("Nenhum dado encontrado para a consulta atual.")
    st.stop()

# Tabela
st.subheader("Tabela")
st.dataframe(df, use_container_width=True)

# Gráfico
st.subheader("Distribuição de alunos por série")
fig = px.bar(df, x="categoria", y="qtd_alunos", text="qtd_alunos")
fig.update_traces(textposition="outside")
fig.update_layout(height=480, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# Download
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Baixar CSV", csv, file_name="alunos_por_serie.csv", mime="text/csv")
