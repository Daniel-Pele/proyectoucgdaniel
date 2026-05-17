import streamlit as st
import datetime

st.set_page_config(page_title="Proyecto Final", layout="centered")

st.title("Proyecto Final")

# ----- Menú lateral: PARÁMETROS -----
st.sidebar.header("PARÁMETROS")

partido = st.sidebar.text_input(
    "PARTIDO",
    value="Real Madrid vs Barcelona"
)

fecha = st.sidebar.date_input(
    "FECHA",
    value=datetime.date(2026, 5, 23)
)

hora = st.sidebar.time_input(
    "HORA DEL PARTIDO",
    value=datetime.time(18, 0)
)

opcion = st.sidebar.selectbox(
    "OPCIÓN A ANALIZAR",
    ["1 (Local Gana)", "X (Empate)", "2 (Visitante Gana)"]
)

analizar = st.sidebar.button("ANALIZAR")

# ----- Resultado -----
if analizar:
    st.subheader("Resultado del análisis")
    st.write(f"**Partido:** {partido}")
    st.write(f"**Fecha:** {fecha.strftime('%d/%m/%Y')}")
    st.write(f"**Hora:** {hora.strftime('%H:%M')}")
    st.write(f"**Opción analizada:** {opcion}")
    st.success("Análisis generado correctamente.")
else:
    st.info("Completa los parámetros en el menú lateral y presiona ANALIZAR.")
