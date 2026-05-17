import streamlit as st
import datetime
import math
import pandas as pd

st.set_page_config(page_title="Proyecto Final - Modelo Hibrido", layout="wide")

st.title("Proyecto Final")
st.subheader("Modelo Hibrido de Pronosticos Deportivos")
st.caption("Elo - Dixon-Coles (Poisson) - Ensamblado")

# ----- MENU LATERAL: PARAMETROS -----
st.sidebar.header("PARAMETROS")
partido = st.sidebar.text_input("PARTIDO", value="Real Madrid vs Barcelona")
fecha = st.sidebar.date_input("FECHA", value=datetime.date(2026, 5, 23))
hora = st.sidebar.time_input("HORA DEL PARTIDO", value=datetime.time(18, 0))
capital = st.sidebar.number_input("CAPITAL DE REFERENCIA (USD)", min_value=1.0, value=20.0, step=1.0)
cuota_minima = st.sidebar.number_input("FILTRO - CUOTA MINIMA", min_value=1.0, value=1.30, step=0.05)
analizar = st.sidebar.button("ANALIZAR")

# ----- DATOS DE LOS EQUIPOS (para calcular P) -----
st.markdown("### 1. Datos de los equipos (la app calcula P)")
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
    # --- Elo: cuota de victoria local (0 a 1) ---
    exp_local = 1 / (1 + 10 ** (-((elo_l + vent) - elo_v) / 400))

    # --- Matriz de marcadores Poisson + correccion Dixon-Coles ---
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

    # --- Ensamblado 1X2: Elo + Poisson ---
    ratio_poisson = p_home_p / (p_home_p + p_away_p)
    ratio_final = peso_elo * exp_local + (1 - peso_elo) * ratio_poisson
    p_local = (1 - p_draw) * ratio_final
    p_visit = (1 - p_draw) * (1 - ratio_final)

    # --- Mercados derivados ---
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

    # --- Tarjetas (Poisson) ---
    p_tarj_si = 1 - sum(poisson(k, tarjetas) for k in range(4))

    # --- Top 3 marcadores ---
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

probs = calcular_probabilidades(
    elo_local, elo_visit, ventaja, goles_local, goles_visit, rho, tarjetas_esp
)

orden = list(probs.keys())
n = len(orden)
if "cuotas" not in st.session_state or len(st.session_state.cuotas) != n:
    st.session_state.cuotas = [0.0] * n

st.markdown("### 2. Ingresa solo la Cuota promedio de cada mercado")
st.info("La columna P la calcula el modelo. Tu solo llenas la Cuota. Luego presiona ANALIZAR.")

tabla = pd.DataFrame({
    "Opcion": [k[0] for k in orden],
    "Evento posible": [k[1] for k in orden],
    "Probabilidad (P)": [round(probs[k], 4) for k in orden],
    "Cuota promedio": st.session_state.cuotas,
})

editado = st.data_editor(
    tabla,
    disabled=["Opcion", "Evento posible", "Probabilidad (P)"],
    hide_index=True,
    use_container_width=True,
    key="editor",
)
st.session_state.cuotas = list(editado["Cuota promedio"])

columnas_cuadro = [
    "Opcion", "Evento posible", "Probabilidad de exito (P)",
    "Valor Esperado (EV)", "Value Index", "Kelly fraccional (1/2-Kelly USD)",
]

def calcular_cuadro(df, capital):
    filas = []
    for _, r in df.iterrows():
        P = float(r["Probabilidad (P)"])
        cuota = float(r["Cuota promedio"])
        b = cuota - 1
        if b > 0:
            EV = P * b - (1 - P)
            value_index = EV / b
        else:
            EV = 0.0
            value_index = 0.0
        kelly = max((value_index / 2) * capital, 0.0)
        filas.append({
            "Opcion": r["Opcion"],
            "Evento posible": r["Evento posible"],
            "Probabilidad de exito (P)": round(P, 2),
            "Valor Esperado (EV)": round(EV, 4),
            "Value Index": round(value_index, 4),
            "Kelly fraccional (1/2-Kelly USD)": round(kelly, 2),
            "Cuota": round(cuota, 2),
        })
    return pd.DataFrame(filas)

if analizar:
    resultado = calcular_cuadro(editado, capital)

    st.markdown("---")
    st.markdown(f"## Analisis: {partido}")
    st.write(
        f"**Fecha:** {fecha.strftime('%d/%m/%Y')}  |  "
        f"**Hora:** {hora.strftime('%H:%M')}  |  "
        f"**Capital:** {capital:.2f} USD"
    )

    st.markdown("### 3. Cuadro final consolidado (todas las opciones)")
    st.dataframe(resultado[columnas_cuadro], hide_index=True, use_container_width=True)

    validas = resultado[
        (resultado["Cuota"] > cuota_minima) & (resultado["Valor Esperado (EV)"] > 0)
    ]

    st.markdown("### 4. Recomendacion final - Apuestas validas")
    st.caption(f"Filtro: Cuota > {cuota_minima:.2f}  Y  EV > 0")
    if len(validas) == 0:
        st.warning("Ninguna opcion cumple el filtro. No se recomienda apostar.")
    else:
        st.success(f"{len(validas)} opcion(es) cumplen el filtro:")
        st.dataframe(validas[columnas_cuadro], hide_index=True, use_container_width=True)
        total = validas["Kelly fraccional (1/2-Kelly USD)"].sum()
        st.metric("Inversion total sugerida (1/2-Kelly)", f"${total:.2f}")
else:
    st.info("Ingresa datos y cuotas, luego presiona ANALIZAR en el menu lateral.")
