import streamlit as st
import datetime
import math
import pandas as pd

st.set_page_config(page_title="Proyecto Final - Modelo Hibrido", layout="wide")

# ----- TEMA OSCURO + DORADO -----
st.markdown(
    """
    <style>
    .stApp { background-color: #0E1A2B; color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #16263D; }
    h1, h2, h3, h4, h5, h6 { color: #F5C518 !important; }
    label, p, span, div { color: #FFFFFF; }
    .stButton button {
        background-color: #F5C518; color: #0E1A2B;
        font-weight: bold; border: none; width: 100%;
    }
    [data-testid="stMetric"] {
        background-color: #16263D; border: 1px solid #F5C518;
        border-radius: 8px; padding: 12px;
    }
    [data-testid="stMetricValue"] { color: #F5C518; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Proyecto Final")
st.subheader("Modelo Hibrido de Pronosticos Deportivos")
st.caption("Elo - Dixon-Coles (Poisson) - Ensamblado")

# ----- MENU LATERAL: PARAMETROS -----
st.sidebar.header("PARAMETROS")
partido = st.sidebar.text_input("PARTIDO", value="Real Madrid vs Barcelona")
fecha = st.sidebar.date_input("FECHA", value=datetime.date(2026, 5, 23))
hora = st.sidebar.time_input("HORA DEL PARTIDO", value=datetime.time(18, 0))
st.sidebar.markdown("---")
analizar = st.sidebar.button("ANALIZAR")

# ----- DATOS DE LOS EQUIPOS -----
st.markdown("### 1. Datos de los equipos")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Equipo LOCAL**")
    elo_local = st.number_input("Elo Local", value=1700.0, step=10.0)
    goles_local = st.number_input("Goles esperados Local", min_value=0.1, value=1.6, step=0.1)
with c2:
    st.markdown("**Equipo VISITANTE**")
    elo_visit = st.number_input("Elo Visitante", value=1650.0, step=10.0)
    goles_visit = st.number_input("Goles esperados Visitante", min_value=0.1, value=1.1, step=0.1)

c3, c4, c5 = st.columns(3)
with c3:
    ventaja = st.number_input("Ventaja de localia (Elo)", value=60.0, step=5.0)
with c4:
    rho = st.number_input("Rho Dixon-Coles", value=-0.05, step=0.01, format="%.2f")
with c5:
    tarjetas_esp = st.number_input("Tarjetas esperadas (total)", min_value=0.1, value=4.0, step=0.5)

peso_elo = st.slider("Peso del modelo Elo en el 1X2 (resto = Poisson)", 0.0, 1.0, 0.5, 0.05)

# ----- MODELO -----
def poisson(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def tau(x, y, lam, mu, rho):
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    if x == 0 and y == 1:
        return 1 + lam * rho
    if x == 1 and y == 0:
        return 1 + mu * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0

def calcular_probabilidades(elo_l, elo_v, vent, lam, mu, rho, tarjetas):
    exp_local = 1 / (1 + 10 ** (-((elo_l + vent) - elo_v) / 400))

    nmax = 9
    matriz = [[0.0] * nmax for _ in range(nmax)]
    total = 0.0
    for x in range(nmax):
        for y in range(nmax):
            p = poisson(x, lam) * poisson(y, mu) * tau(x, y, lam, mu, rho)
            matriz[x][y] = p
            total += p
    for x in range(nmax):
        for y in range(nmax):
            matriz[x][y] /= total

    p_home_p = sum(matriz[x][y] for x in range(nmax) for y in range(nmax) if x > y)
    p_draw = sum(matriz[i][i] for i in range(nmax))
    p_away_p = sum(matriz[x][y] for x in range(nmax) for y in range(nmax) if x < y)

    ratio_poisson = p_home_p / (p_home_p + p_away_p)
    ratio_final = peso_elo * exp_local + (1 - peso_elo) * ratio_poisson
    p_local = (1 - p_draw) * ratio_final
    p_visit = (1 - p_draw) * (1 - ratio_final)

    p_btts_si = sum(matriz[x][y] for x in range(1, nmax) for y in range(1, nmax))
    p_over25 = sum(matriz[x][y] for x in range(nmax) for y in range(nmax) if x + y >= 3)
    p_no_gol = matriz[0][0]
    p_first_local = (1 - p_no_gol) * lam / (lam + mu)
    p_first_visit = (1 - p_no_gol) * mu / (lam + mu)

    def goles_equipo(es_local, umbral):
        prob = 0.0
        for x in range(nmax):
            for y in range(nmax):
                g = x if es_local else y
                if g >= umbral:
                    prob += matriz[x][y]
        return prob

    p_tarj_si = 1 - sum(poisson(k, tarjetas) for k in range(4))

    celdas = []
    for x in range(nmax):
        for y in range(nmax):
            celdas.append((f"{x}-{y}", matriz[x][y]))
    celdas.sort(key=lambda c: c[1], reverse=True)
    top3 = celdas[:3]

    return {
        ("Resultado 1X2", "Local"): p_local,
        ("Resultado 1X2", "Empate"): p_draw,
        ("Resultado 1X2", "Visitante"): p_visit,
        ("Equipo que marca primero", "Local"): p_first_local,
        ("Equipo que marca primero", "Visitante"): p_first_visit,
        ("Equipo que marca primero", "Sin gol"): p_no_gol,
        ("Ambos marcan (BTTS)", "Si"): p_btts_si,
        ("Ambos marcan (BTTS)", "No"): 1 - p_btts_si,
        ("Total goles >2.5", "Si"): p_over25,
        ("Total goles >2.5", "No"): 1 - p_over25,
        ("Goles totales Local", ">0.5"): goles_equipo(True, 1),
        ("Goles totales Local", ">1.5"): goles_equipo(True, 2),
        ("Goles totales Local", ">2.5"): goles_equipo(True, 3),
        ("Goles totales Visitante", ">0.5"): goles_equipo(False, 1),
        ("Goles totales Visitante", ">1.5"): goles_equipo(False, 2),
        ("Goles totales Visitante", ">2.5"): goles_equipo(False, 3),
        ("Cualquier equipo gana", "Local o Visitante (No empate)"): 1 - p_draw,
        ("Probabilidad total tarjetas", ">3.5 Si"): p_tarj_si,
        ("Probabilidad total tarjetas", ">3.5 No"): 1 - p_tarj_si,
        ("Marcadores mas probables", f"Top 1: {top3[0][0]}"): top3[0][1],
        ("Marcadores mas probables", f"Top 2: {top3[1][0]}"): top3[1][1],
        ("Marcadores mas probables", f"Top 3: {top3[2][0]}"): top3[2][1],
    }

if analizar:
    probs = calcular_probabilidades(
        elo_local, elo_visit, ventaja, goles_local, goles_visit, rho, tarjetas_esp
    )

    filas = []
    for (opcion, evento), P in probs.items():
        cuota_justa = (1 / P) if P > 0 else 0.0
        filas.append({
            "Opcion": opcion,
            "Evento posible": evento,
            "Probabilidad de exito (P)": round(P, 4),
            "Probabilidad %": f"{P * 100:.2f}%",
            "Cuota justa (1/P)": round(cuota_justa, 2),
        })
    resultado = pd.DataFrame(filas)

    st.markdown("---")
    st.markdown(f"## Analisis: {partido}")
    st.write(f"**Fecha:** {fecha.strftime('%d/%m/%Y')}  |  **Hora:** {hora.strftime('%H:%M')}")

    p_loc = probs[("Resultado 1X2", "Local")]
    p_emp = probs[("Resultado 1X2", "Empate")]
    p_vis = probs[("Resultado 1X2", "Visitante")]

    st.markdown("### Resumen del resultado (1X2)")
    r1, r2, r3 = st.columns(3)
    r1.metric("LOCAL gana", f"{p_loc * 100:.1f}%", f"Cuota justa {1/p_loc:.2f}")
    r2.metric("EMPATE", f"{p_emp * 100:.1f}%", f"Cuota justa {1/p_emp:.2f}")
    r3.metric("VISITANTE gana", f"{p_vis * 100:.1f}%", f"Cuota justa {1/p_vis:.2f}")

    favorito = max(
        [("LOCAL", p_loc), ("EMPATE", p_emp), ("VISITANTE", p_vis)],
        key=lambda t: t[1],
    )
    st.success(f"Resultado mas probable: {favorito[0]} ({favorito[1] * 100:.1f}%)")

    st.markdown("### Cuadro final consolidado (todas las opciones)")
    st.dataframe(resultado, hide_index=True, use_container_width=True)
else:
    st.info("Llena los datos de los equipos y presiona ANALIZAR en el menu lateral.")
