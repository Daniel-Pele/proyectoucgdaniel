import streamlit as st
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
    .stApp label, .stApp p, .stMarkdown { color: #FFFFFF !important; }
    .stButton button {
        background-color: #F5C518; color: #0E1A2B;
        font-weight: bold; border: none; width: 100%;
    }
    input, textarea { color: #0E1A2B !important; }
    [data-baseweb="select"] * { color: #0E1A2B !important; }
    [data-testid="stMetric"] {
        background-color: #16263D; border: 1px solid #F5C518;
        border-radius: 8px; padding: 12px;
    }
    [data-testid="stMetricValue"] { color: #F5C518 !important; }
    [data-testid="stMetricLabel"] { color: #FFFFFF !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Proyecto Final")
st.subheader("Modelo Hibrido de Pronosticos Deportivos")
st.caption("Elo - Dixon-Coles (Poisson) - Ensamblado")

# ----- BASE DE EQUIPOS POR LIGA (Elo referencial) -----
# Los valores Elo son referenciales (escala tipo ClubElo) y son editables
# en pantalla. Los goles esperados se derivan del Elo de cada equipo.
LIGAS = {
    "LigaPro Ecuador": {
        "Independiente del Valle": 1720, "LDU Quito": 1700,
        "Barcelona SC": 1680, "Emelec": 1620, "Universidad Catolica": 1600,
        "Aucas": 1590, "Deportivo Cuenca": 1590, "Orense": 1580,
        "El Nacional": 1580, "Mushuc Runa": 1580, "Macara": 1570,
        "Libertad": 1570, "Tecnico Universitario": 1560, "Delfin": 1560,
        "Manta": 1550, "Imbabura": 1540, "Vinotinto": 1540,
    },
    "Premier League (Inglaterra)": {
        "Manchester City": 1950, "Arsenal": 1900, "Liverpool": 1900,
        "Chelsea": 1800, "Tottenham": 1790, "Manchester United": 1780,
        "Newcastle": 1770, "Aston Villa": 1760, "Brighton": 1720,
        "West Ham": 1700, "Crystal Palace": 1680, "Bournemouth": 1670,
        "Fulham": 1670, "Brentford": 1670, "Everton": 1650,
        "Nottingham Forest": 1640, "Wolves": 1640, "Leicester": 1620,
        "Ipswich": 1580, "Southampton": 1580,
    },
    "LaLiga (Espana)": {
        "Real Madrid": 1960, "Barcelona": 1910, "Atletico Madrid": 1850,
        "Athletic Bilbao": 1760, "Real Sociedad": 1740, "Villarreal": 1730,
        "Girona": 1730, "Real Betis": 1720, "Sevilla": 1700,
        "Valencia": 1690, "Osasuna": 1670, "Celta Vigo": 1660,
        "Mallorca": 1660, "Rayo Vallecano": 1650, "Getafe": 1650,
        "Las Palmas": 1630, "Espanyol": 1620, "Alaves": 1620,
        "Leganes": 1590, "Valladolid": 1580,
    },
    "Serie A (Italia)": {
        "Inter": 1900, "Napoli": 1850, "Atalanta": 1830, "Juventus": 1820,
        "Milan": 1800, "Roma": 1760, "Lazio": 1760, "Fiorentina": 1740,
        "Bologna": 1730, "Torino": 1680, "Udinese": 1660, "Genoa": 1650,
        "Como": 1640, "Verona": 1620, "Cagliari": 1620, "Lecce": 1610,
        "Empoli": 1610, "Parma": 1610, "Monza": 1600, "Venezia": 1590,
    },
    "Bundesliga (Alemania)": {
        "Bayern Munich": 1930, "Bayer Leverkusen": 1880,
        "Borussia Dortmund": 1820, "RB Leipzig": 1810, "Stuttgart": 1750,
        "Eintracht Frankfurt": 1740, "Freiburg": 1700, "Mainz": 1680,
        "Werder Bremen": 1670, "Borussia Monchengladbach": 1670,
        "Wolfsburg": 1670, "Augsburg": 1650, "Hoffenheim": 1650,
        "Union Berlin": 1650, "Heidenheim": 1620, "St Pauli": 1610,
        "Bochum": 1580, "Holstein Kiel": 1570,
    },
    "Ligue 1 (Francia)": {
        "PSG": 1920, "Monaco": 1780, "Marseille": 1770, "Lille": 1760,
        "Nice": 1730, "Lyon": 1730, "Lens": 1720, "Rennes": 1700,
        "Brest": 1690, "Strasbourg": 1660, "Toulouse": 1660,
        "Reims": 1650, "Nantes": 1630, "Auxerre": 1620, "Le Havre": 1610,
        "Angers": 1600, "Montpellier": 1600, "Saint-Etienne": 1600,
    },
    "Liga MX (Mexico)": {
        "America": 1780, "Monterrey": 1770, "Tigres UANL": 1760,
        "Cruz Azul": 1740, "Toluca": 1720, "Pachuca": 1700,
        "Guadalajara": 1700, "Leon": 1690, "Pumas UNAM": 1680,
        "Atlas": 1650, "Santos Laguna": 1640, "Tijuana": 1640,
        "San Luis": 1630, "Necaxa": 1630, "Juarez": 1620,
        "Puebla": 1620, "Mazatlan": 1610, "Queretaro": 1600,
    },
    "Brasileirao (Brasil)": {
        "Palmeiras": 1830, "Botafogo": 1820, "Flamengo": 1820,
        "Atletico Mineiro": 1760, "Internacional": 1750, "Sao Paulo": 1740,
        "Fortaleza": 1740, "Cruzeiro": 1720, "Bahia": 1700,
        "Gremio": 1700, "Corinthians": 1690, "Fluminense": 1690,
        "Bragantino": 1680, "Athletico Paranaense": 1680,
        "Vasco da Gama": 1670, "Juventude": 1620, "Vitoria": 1620,
        "Criciuma": 1610,
    },
    "Liga Argentina": {
        "River Plate": 1820, "Boca Juniors": 1780, "Racing Club": 1760,
        "Velez Sarsfield": 1740, "Estudiantes": 1720, "Talleres": 1720,
        "San Lorenzo": 1700, "Independiente": 1690, "Argentinos Juniors": 1690,
        "Huracan": 1680, "Lanus": 1670, "Defensa y Justicia": 1670,
        "Rosario Central": 1670, "Newells": 1650, "Gimnasia LP": 1640,
        "Banfield": 1640,
    },
}

def fuerza(elo):
    # Normaliza el Elo a un indice 0..1 (1500 = flojo, 2000 = top)
    s = (elo - 1500.0) / 500.0
    return max(0.0, min(1.0, s))

def goles_favor(elo):
    # Mas Elo -> marca mas (rango aprox 0.7 a 1.6) - partidos mas cerrados
    return round(0.7 + 0.9 * fuerza(elo), 2)

def goles_contra(elo):
    # Mas Elo -> recibe menos (rango aprox 1.4 a 0.7)
    return round(1.4 - 0.7 * fuerza(elo), 2)

# ----- MENU LATERAL: PARAMETROS -----
st.sidebar.header("PARAMETROS")

liga = st.sidebar.selectbox("LIGA", list(LIGAS.keys()))
equipos_liga = list(LIGAS[liga].keys())

equipo_local = st.sidebar.selectbox("EQUIPO LOCAL", equipos_liga, index=0)
equipo_visit = st.sidebar.selectbox("EQUIPO VISITANTE", equipos_liga, index=1)

fecha = st.sidebar.text_input("FECHA (dd/mm/aaaa)", value="17/05/2026")
horas_disponibles = [
    "12:00", "13:00", "14:00", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00",
    "20:30", "21:00", "21:30", "22:00",
]
hora = st.sidebar.selectbox("HORA DEL PARTIDO", horas_disponibles, index=9)
st.sidebar.markdown("---")
analizar = st.sidebar.button("ANALIZAR")

partido = equipo_local + " vs " + equipo_visit

if equipo_local == equipo_visit:
    st.warning("El equipo local y el visitante no pueden ser el mismo. Cambia uno de los dos.")

# ----- DATOS DE LOS EQUIPOS (autollenados desde la liga, editables) -----
elo_l_base = float(LIGAS[liga][equipo_local])
elo_v_base = float(LIGAS[liga][equipo_visit])

# Goles esperados del partido segun fuerza de cada equipo
gf_l, gc_l = goles_favor(elo_l_base), goles_contra(elo_l_base)
gf_v, gc_v = goles_favor(elo_v_base), goles_contra(elo_v_base)
lam_base = round((gf_l + gc_v) / 2.0 * 1.05, 2)   # ataque local + factor localia
mu_base = round((gf_v + gc_l) / 2.0 * 0.88, 2)    # ataque visitante

st.markdown("### 1. Datos de los equipos (autollenados desde la liga, editables)")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**" + equipo_local + " (LOCAL)**")
    elo_local = st.number_input(
        "Elo Local", value=elo_l_base, step=10.0,
        key="elo_l_" + liga + equipo_local,
    )
    goles_local = st.number_input(
        "Goles esperados Local", min_value=0.1, value=lam_base, step=0.1,
        key="gl_" + liga + equipo_local + equipo_visit,
    )
with c2:
    st.markdown("**" + equipo_visit + " (VISITANTE)**")
    elo_visit = st.number_input(
        "Elo Visitante", value=elo_v_base, step=10.0,
        key="elo_v_" + liga + equipo_visit,
    )
    goles_visit = st.number_input(
        "Goles esperados Visitante", min_value=0.1, value=mu_base, step=0.1,
        key="gv_" + liga + equipo_local + equipo_visit,
    )

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

if analizar and equipo_local != equipo_visit:
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
    st.write(f"**Liga:** {liga}  |  **Fecha:** {fecha}  |  **Hora:** {hora}")

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
    st.info("Elige liga y equipos, revisa los datos y presiona ANALIZAR en el menu lateral.")
