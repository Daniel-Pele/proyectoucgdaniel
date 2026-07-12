import streamlit as st
import math
import pandas as pd
import hashlib
import re
import random
import requests
from datetime import datetime
from supabase import create_client, Client

# ================================================================
# BASE DE DATOS (Supabase - persiste en Streamlit Cloud)
# ================================================================
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def registrar_usuario(nombre, correo, password):
    try:
        db = get_supabase()
        db.table("usuarios").insert({
            "nombre": nombre,
            "correo": correo,
            "password": hash_password(password),
            "fecha_reg": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }).execute()
        return True, "Registro exitoso."
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False, "Ese correo ya esta registrado."
        return False, f"Error al registrar: {e}"

def login_usuario(correo, password):
    db = get_supabase()
    res = db.table("usuarios").select("id, nombre, plan, pronosticos_hoy, fecha_ultimo_uso").eq("correo", correo).eq("password", hash_password(password)).execute()
    if res.data:
        fila = res.data[0]
        db.table("usuarios").update({"ultimo_login": datetime.now().strftime("%Y-%m-%d %H:%M")}).eq("id", fila["id"]).execute()
        return fila
    return None

def obtener_usuarios():
    db = get_supabase()
    res = db.table("usuarios").select("id, nombre, correo, plan, pronosticos_hoy, fecha_reg, ultimo_login").order("fecha_reg", desc=True).execute()
    return pd.DataFrame(res.data)

def total_usuarios():
    db = get_supabase()
    res = db.table("usuarios").select("id", count="exact").execute()
    return res.count or 0

def cambiar_plan(usuario_id, nuevo_plan):
    db = get_supabase()
    db.table("usuarios").update({"plan": nuevo_plan, "pronosticos_hoy": 0}).eq("id", usuario_id).execute()

LIMITES = {"gratis": 3, "basic": 5, "pro": 999999}
WHATSAPP = "https://wa.me/593993299554?text=Hola,%20quiero%20suscribirme%20al%20plan%20de%20pronosticos"

def verificar_limite():
    uid  = st.session_state.get("usuario_id")
    plan = st.session_state.get("usuario_plan", "gratis")
    if uid == 0:
        return True
    hoy  = datetime.now().strftime("%Y-%m-%d")
    db   = get_supabase()
    res  = db.table("usuarios").select("pronosticos_hoy, fecha_ultimo_uso, plan").eq("id", uid).execute()
    if not res.data:
        return False
    datos = res.data[0]
    plan  = datos.get("plan", "gratis")
    st.session_state["usuario_plan"] = plan
    limite = LIMITES.get(plan, 3)
    if datos.get("fecha_ultimo_uso") != hoy:
        db.table("usuarios").update({"pronosticos_hoy": 0, "fecha_ultimo_uso": hoy}).eq("id", uid).execute()
        return True
    usado = datos.get("pronosticos_hoy", 0)
    return usado < limite

def registrar_pronostico():
    uid = st.session_state.get("usuario_id")
    if uid == 0:
        return
    hoy = datetime.now().strftime("%Y-%m-%d")
    db  = get_supabase()
    res = db.table("usuarios").select("pronosticos_hoy, fecha_ultimo_uso").eq("id", uid).execute()
    if res.data:
        datos = res.data[0]
        if datos.get("fecha_ultimo_uso") != hoy:
            db.table("usuarios").update({"pronosticos_hoy": 1, "fecha_ultimo_uso": hoy}).eq("id", uid).execute()
        else:
            nuevo = (datos.get("pronosticos_hoy") or 0) + 1
            db.table("usuarios").update({"pronosticos_hoy": nuevo}).eq("id", uid).execute()

# ================================================================
# CREDENCIALES DE ADMIN (cambiar antes de desplegar)
# ================================================================
ADMIN_CORREO   = "admin@pronosticos.com"
ADMIN_PASSWORD = "Admin2026!"

# ================================================================
# CONFIGURACION
# ================================================================
st.set_page_config(page_title="Proyecto Final - Modelo Hibrido", layout="wide")

# ----- TEMA OSCURO + DORADO -----
st.markdown(
    """
    <style>
    .stApp { background-color: #0E1A2B; color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #16263D; }
    h1, h2, h3, h4, h5, h6 { color: #F5C518 !important; }
    .stApp label, .stApp p, .stMarkdown { color: #FFFFFF !important; }
    .stButton button, .stFormSubmitButton button {
        background-color: #F5C518 !important; color: #0E1A2B !important;
        font-weight: bold !important; border: none !important; width: 100% !important;
        border-radius: 8px !important; font-size: 16px !important;
        padding: 10px !important; cursor: pointer !important;
    }
    .stButton button:hover, .stFormSubmitButton button:hover {
        background-color: #d4a800 !important; color: #0E1A2B !important;
    }
    .stLinkButton a {
        background-color: #25D366 !important; color: #FFFFFF !important;
        font-weight: bold !important; border-radius: 8px !important;
        padding: 10px 20px !important; text-decoration: none !important;
        display: block !important; text-align: center !important;
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

# ================================================================
# HEADER: titulo izquierda | auth derecha
# ================================================================
if "usuario_id"   not in st.session_state: st.session_state.usuario_id   = None
if "usuario_nom"  not in st.session_state: st.session_state.usuario_nom  = None
if "usuario_plan" not in st.session_state: st.session_state.usuario_plan = "gratis"
if "es_admin"     not in st.session_state: st.session_state.es_admin     = False
if "vista_auth"   not in st.session_state: st.session_state.vista_auth   = None

# ================================================================
# PORTADA PRINCIPAL
# ================================================================
if st.session_state.usuario_id is None:
    import os
    for nombre in ["logo.png", "logo.jpeg", "logo.jpg"]:
        if os.path.exists(nombre) and os.path.getsize(nombre) > 0:
            st.image(nombre, use_container_width=True)
            break
    else:
        st.markdown("""
        <div style="text-align:center; padding:40px; border:2px solid #F5C518; border-radius:20px; background:#16263D;">
            <div style="font-size:40px; font-weight:900; color:#F5C518;">FUTBOL 1, 2, 3...</div>
            <div style="font-size:22px; color:#FFFFFF; margin:10px 0;">MODELO HIBRIDO DE PRONOSTICOS DEPORTIVOS</div>
            <div style="font-size:14px; color:#AAAAAA;">Elo &bull; Dixon-Coles (Poisson) &bull; Ensamblado</div>
        </div>""", unsafe_allow_html=True)

    b1, b2, b3 = st.columns([2, 1, 1])
    with b2:
        if st.button("Iniciar sesion", use_container_width=True):
            st.session_state.vista_auth = "login"
    with b3:
        if st.button("Registrarse", use_container_width=True):
            st.session_state.vista_auth = "registro"

else:
    col_titulo, col_auth = st.columns([3, 1])
    with col_titulo:
        st.markdown("### Futbol 1, 2, 3... - Modelo Hibrido de Pronosticos Deportivos")
        st.caption("Elo - Dixon-Coles (Poisson) - Ensamblado")
    with col_auth:
        st.markdown(f"**{st.session_state.usuario_nom}**")
        plan = st.session_state.get('usuario_plan', 'gratis')
        st.caption(f"Plan {plan.upper()}")
        if st.button("Cerrar sesion"):
            st.session_state.usuario_id  = None
            st.session_state.usuario_nom = None
            st.session_state.es_admin    = False
            st.session_state.vista_auth  = None
            st.rerun()

# ================================================================
# PANEL DE LOGIN
# ================================================================
if st.session_state.vista_auth == "login" and st.session_state.usuario_id is None:
    st.markdown("---")
    st.markdown("### Iniciar sesion")
    with st.form("form_login"):
        correo_l   = st.text_input("Correo electronico")
        password_l = st.text_input("Contrasena", type="password")
        submit_l   = st.form_submit_button("Entrar")

    if submit_l:
        if correo_l == ADMIN_CORREO and password_l == ADMIN_PASSWORD:
            st.session_state.usuario_id  = 0
            st.session_state.usuario_nom = "Administrador"
            st.session_state.es_admin    = True
            st.session_state.vista_auth  = None
            st.success("Bienvenido, Administrador.")
            st.rerun()
        else:
            fila = login_usuario(correo_l, password_l)
            if fila:
                st.session_state.usuario_id   = fila["id"]
                st.session_state.usuario_nom  = fila["nombre"]
                st.session_state.usuario_plan = fila.get("plan", "gratis")
                st.session_state.es_admin     = False
                st.session_state.vista_auth   = None
                st.success(f"Bienvenido, {fila['nombre']}.")
                st.rerun()
            else:
                st.error("Correo o contrasena incorrectos.")
    st.stop()

# ================================================================
# PANEL DE REGISTRO
# ================================================================
if st.session_state.vista_auth == "registro" and st.session_state.usuario_id is None:
    st.markdown("---")
    st.markdown("### Crear cuenta")
    with st.form("form_registro"):
        nombre_r   = st.text_input("Nombre completo")
        correo_r   = st.text_input("Correo electronico")
        password_r = st.text_input("Contrasena", type="password")
        password_r2= st.text_input("Confirmar contrasena", type="password")
        submit_r   = st.form_submit_button("Registrarse")

    if submit_r:
        if not nombre_r or not correo_r or not password_r:
            st.error("Completa todos los campos.")
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", correo_r):
            st.error("Correo invalido.")
        elif len(password_r) < 6:
            st.error("La contrasena debe tener al menos 6 caracteres.")
        elif password_r != password_r2:
            st.error("Las contrasenas no coinciden.")
        else:
            ok, msg = registrar_usuario(nombre_r, correo_r, password_r)
            if ok:
                st.success(msg + " Ya puedes iniciar sesion.")
                st.session_state.vista_auth = "login"
                st.rerun()
            else:
                st.error(msg)
    st.stop()

# ================================================================
# PANEL DE ADMINISTRADOR
# ================================================================
if st.session_state.es_admin:
    st.markdown("---")
    st.markdown("## Panel de Administrador")

    total = total_usuarios()
    df_u  = obtener_usuarios()

    m1, m2 = st.columns(2)
    m1.metric("Total de usuarios registrados", total)
    m2.metric("Ultimo registro",
              df_u["fecha_reg"].iloc[0] if not df_u.empty else "Sin registros")

    st.markdown("### Lista de usuarios y planes")
    if df_u.empty:
        st.info("No hay usuarios registrados aun.")
    else:
        for _, row in df_u.iterrows():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.write(f"**{row['nombre']}** — {row['correo']}")
            c2.write(f"Plan: `{row.get('plan','gratis')}`")
            c3.write(f"Usos hoy: {row.get('pronosticos_hoy', 0)}")
            nuevo_plan = c4.selectbox(
                "Cambiar",
                ["gratis", "basic", "pro"],
                index=["gratis","basic","pro"].index(row.get("plan","gratis")),
                key=f"plan_{row['id']}"
            )
            if nuevo_plan != row.get("plan", "gratis"):
                cambiar_plan(row["id"], nuevo_plan)
                st.success(f"Plan de {row['nombre']} cambiado a {nuevo_plan}")
                st.rerun()
            st.markdown("---")
    st.stop()

# ================================================================
# ACCESO RESTRINGIDO
# ================================================================
if st.session_state.usuario_id is None:
    st.markdown("---")
    st.info("Inicia sesion o registrate para acceder al pronosticador.")
    st.stop()

# ================================================================
# APLICACION PRINCIPAL (solo usuarios autenticados)
# ================================================================

# ----- BASE DE EQUIPOS POR LIGA (Elo referencial) -----
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
    "Copa Mundial 2026": {
        "Qatar": 1590, "Ecuador": 1620, "Senegal": 1700, "Paises Bajos": 1780,
        "Inglaterra": 1820, "Iran": 1640, "EE.UU.": 1700, "Gales": 1660,
        "Argentina": 1845, "Arabia Saudita": 1620, "Mexico": 1710, "Polonia": 1680,
        "Francia": 1840, "Australia": 1650, "Dinamarca": 1730, "Tunez": 1620,
        "Espana": 1810, "Costa Rica": 1600, "Alemania": 1790, "Japon": 1700,
        "Belgica": 1780, "Canada": 1660, "Marruecos": 1710, "Croacia": 1760,
        "Brasil": 1850, "Serbia": 1680, "Suiza": 1720, "Camerun": 1610,
        "Portugal": 1800, "Ghana": 1600, "Uruguay": 1740, "Corea del Sur": 1680,
    },
}

EQUIPOS_MUNDIAL_2026 = {
    "A": [
        {"pais": "Mexico",               "iso": "MEX", "conf": "CONCACAF", "anfitrion": True},
        {"pais": "Sudafrica",            "iso": "RSA", "conf": "CAF"},
        {"pais": "Corea del Sur",        "iso": "KOR", "conf": "AFC"},
        {"pais": "Chequia",              "iso": "CZE", "conf": "UEFA"},
    ],
    "B": [
        {"pais": "Canada",               "iso": "CAN", "conf": "CONCACAF", "anfitrion": True},
        {"pais": "Suiza",                "iso": "SUI", "conf": "UEFA"},
        {"pais": "Qatar",                "iso": "QAT", "conf": "AFC"},
        {"pais": "Bosnia y Herzegovina", "iso": "BIH", "conf": "UEFA"},
    ],
    "C": [
        {"pais": "Brasil",               "iso": "BRA", "conf": "CONMEBOL"},
        {"pais": "Marruecos",            "iso": "MAR", "conf": "CAF"},
        {"pais": "Haiti",                "iso": "HAI", "conf": "CONCACAF"},
        {"pais": "Escocia",              "iso": "SCO", "conf": "UEFA"},
    ],
    "D": [
        {"pais": "Estados Unidos",       "iso": "USA", "conf": "CONCACAF", "anfitrion": True},
        {"pais": "Paraguay",             "iso": "PAR", "conf": "CONMEBOL"},
        {"pais": "Australia",            "iso": "AUS", "conf": "AFC"},
        {"pais": "Turquia",              "iso": "TUR", "conf": "UEFA"},
    ],
    "E": [
        {"pais": "Alemania",             "iso": "GER", "conf": "UEFA"},
        {"pais": "Curazao",              "iso": "CUW", "conf": "CONCACAF"},
        {"pais": "Costa de Marfil",      "iso": "CIV", "conf": "CAF"},
        {"pais": "Ecuador",              "iso": "ECU", "conf": "CONMEBOL"},
    ],
    "F": [
        {"pais": "Paises Bajos",         "iso": "NED", "conf": "UEFA"},
        {"pais": "Japon",                "iso": "JPN", "conf": "AFC"},
        {"pais": "Tunez",                "iso": "TUN", "conf": "CAF"},
        {"pais": "Suecia",               "iso": "SWE", "conf": "UEFA"},
    ],
    "G": [
        {"pais": "Belgica",              "iso": "BEL", "conf": "UEFA"},
        {"pais": "Egipto",               "iso": "EGY", "conf": "CAF"},
        {"pais": "Iran",                 "iso": "IRN", "conf": "AFC"},
        {"pais": "Nueva Zelanda",        "iso": "NZL", "conf": "OFC"},
    ],
    "H": [
        {"pais": "Espana",               "iso": "ESP", "conf": "UEFA"},
        {"pais": "Cabo Verde",           "iso": "CPV", "conf": "CAF"},
        {"pais": "Arabia Saudita",       "iso": "KSA", "conf": "AFC"},
        {"pais": "Uruguay",              "iso": "URU", "conf": "CONMEBOL"},
    ],
    "I": [
        {"pais": "Francia",              "iso": "FRA", "conf": "UEFA"},
        {"pais": "Senegal",              "iso": "SEN", "conf": "CAF"},
        {"pais": "Noruega",              "iso": "NOR", "conf": "UEFA"},
        {"pais": "Iraq",                 "iso": "IRQ", "conf": "AFC"},
    ],
    "J": [
        {"pais": "Argentina",            "iso": "ARG", "conf": "CONMEBOL"},
        {"pais": "Argelia",              "iso": "ALG", "conf": "CAF"},
        {"pais": "Austria",              "iso": "AUT", "conf": "UEFA"},
        {"pais": "Jordania",             "iso": "JOR", "conf": "AFC"},
    ],
    "K": [
        {"pais": "Portugal",             "iso": "POR", "conf": "UEFA"},
        {"pais": "Colombia",             "iso": "COL", "conf": "CONMEBOL"},
        {"pais": "Uzbekistan",           "iso": "UZB", "conf": "AFC"},
        {"pais": "DR Congo",             "iso": "COD", "conf": "CAF"},
    ],
    "L": [
        {"pais": "Inglaterra",           "iso": "ENG", "conf": "UEFA"},
        {"pais": "Croacia",              "iso": "CRO", "conf": "UEFA"},
        {"pais": "Ghana",                "iso": "GHA", "conf": "CAF"},
        {"pais": "Panama",               "iso": "PAN", "conf": "CONCACAF"},
    ],
}

LIGAS["Copa Mundial 2026"].update({
    "Sudafrica": 1580, "Chequia": 1670, "Bosnia y Herzegovina": 1640,
    "Haiti": 1530, "Escocia": 1680, "Estados Unidos": 1700,
    "Paraguay": 1650, "Turquia": 1690, "Curazao": 1530,
    "Costa de Marfil": 1680, "Suecia": 1720, "Egipto": 1650,
    "Nueva Zelanda": 1580, "Cabo Verde": 1590, "Noruega": 1740,
    "Iraq": 1590, "Argelia": 1660, "Austria": 1700,
    "Jordania": 1580, "Colombia": 1720, "Uzbekistan": 1620,
    "DR Congo": 1610, "Panama": 1620,
})

def fuerza(elo):
    s = (elo - 1500.0) / 500.0
    return max(0.0, min(1.0, s))

def goles_favor(elo):
    return round(0.7 + 0.9 * fuerza(elo), 2)

def goles_contra(elo):
    return round(1.4 - 0.7 * fuerza(elo), 2)

# ----- MENU LATERAL: PARAMETROS -----
st.sidebar.header("PARAMETROS")

OPCIONES_LIGA = list(LIGAS.keys()) + ["--- Otra liga (libre) ---"]
liga = st.sidebar.selectbox("LIGA", OPCIONES_LIGA)

LIGA_LIBRE = liga == "--- Otra liga (libre) ---"

if LIGA_LIBRE:
    st.sidebar.info("Escribe cualquier equipo del mundo")
    equipo_local = st.sidebar.text_input("EQUIPO LOCAL", placeholder="Ej: Deportivo Cuenca")
    equipo_visit = st.sidebar.text_input("EQUIPO VISITANTE", placeholder="Ej: River Plate")
    if not equipo_local: equipo_local = "Equipo Local"
    if not equipo_visit: equipo_visit = "Equipo Visitante"
    elo_l_base = 1650.0
    elo_v_base = 1650.0
else:
    equipos_liga = list(LIGAS[liga].keys())
    equipo_local = st.sidebar.selectbox("EQUIPO LOCAL", equipos_liga, index=0)
    equipo_visit = st.sidebar.selectbox("EQUIPO VISITANTE", equipos_liga, index=1)
    elo_l_base = float(LIGAS[liga][equipo_local])
    elo_v_base = float(LIGAS[liga][equipo_visit])

st.sidebar.markdown("---")
analizar = st.sidebar.button("ANALIZAR")
mejores_hoy = st.sidebar.button("TOP 5 PARTIDOS RECOMENDADOS")
partidos_hoy = st.sidebar.button("TOP 5 PARTIDOS DE HOY")

partido = equipo_local + " vs " + equipo_visit

if equipo_local == equipo_visit:
    st.warning("El equipo local y el visitante no pueden ser el mismo. Cambia uno de los dos.")

gf_l, gc_l = goles_favor(elo_l_base), goles_contra(elo_l_base)
gf_v, gc_v = goles_favor(elo_v_base), goles_contra(elo_v_base)
lam_base = round((gf_l + gc_v) / 2.0 * 1.05, 2)
mu_base  = round((gf_v + gc_l) / 2.0 * 0.88, 2)

st.markdown("### 1. Datos de los equipos (autollenados desde la liga, editables)")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**" + equipo_local + " (LOCAL)**")
    elo_local = st.number_input("Elo Local", value=elo_l_base, step=10.0,
                                key="elo_l_" + liga + equipo_local)
    goles_local = st.number_input("Goles esperados Local", min_value=0.1, value=lam_base, step=0.1,
                                  key="gl_" + liga + equipo_local + equipo_visit)
with c2:
    st.markdown("**" + equipo_visit + " (VISITANTE)**")
    elo_visit = st.number_input("Elo Visitante", value=elo_v_base, step=10.0,
                                key="elo_v_" + liga + equipo_visit)
    goles_visit = st.number_input("Goles esperados Visitante", min_value=0.1, value=mu_base, step=0.1,
                                  key="gv_" + liga + equipo_local + equipo_visit)

c3, c4, c5 = st.columns(3)
with c3:
    ventaja = st.number_input("Ventaja de localia (Elo)", value=60.0, step=5.0)
with c4:
    rho = st.number_input("Rho Dixon-Coles", value=-0.05, step=0.01, format="%.2f")
with c5:
    tarjetas_esp = st.number_input("Tarjetas esperadas (total)", min_value=0.1, value=4.0, step=0.5)

peso_elo = st.slider("Peso del modelo Elo en el 1X2 (resto = Poisson)", 0.0, 1.0, 0.5, 0.05)

def poisson(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def tau(x, y, lam, mu, rho):
    if x == 0 and y == 0: return 1 - lam * mu * rho
    if x == 0 and y == 1: return 1 + lam * rho
    if x == 1 and y == 0: return 1 + mu * rho
    if x == 1 and y == 1: return 1 - rho
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
    p_draw   = sum(matriz[i][i] for i in range(nmax))
    p_away_p = sum(matriz[x][y] for x in range(nmax) for y in range(nmax) if x < y)

    ratio_poisson = p_home_p / (p_home_p + p_away_p)
    ratio_final   = peso_elo * exp_local + (1 - peso_elo) * ratio_poisson
    p_local = (1 - p_draw) * ratio_final
    p_visit = (1 - p_draw) * (1 - ratio_final)

    p_btts_si = sum(matriz[x][y] for x in range(1, nmax) for y in range(1, nmax))
    p_over25  = sum(matriz[x][y] for x in range(nmax) for y in range(nmax) if x + y >= 3)
    p_no_gol  = matriz[0][0]
    p_first_local = (1 - p_no_gol) * lam / (lam + mu)
    p_first_visit = (1 - p_no_gol) * mu  / (lam + mu)

    def goles_equipo(es_local, umbral):
        prob = 0.0
        for x in range(nmax):
            for y in range(nmax):
                g = x if es_local else y
                if g >= umbral:
                    prob += matriz[x][y]
        return prob

    p_tarj_si = 1 - sum(poisson(k, tarjetas) for k in range(4))

    celdas = [(f"{x}-{y}", matriz[x][y]) for x in range(nmax) for y in range(nmax)]
    celdas.sort(key=lambda c: c[1], reverse=True)
    top3 = celdas[:3]

    return {
        ("Resultado 1X2", "Local"):                              p_local,
        ("Resultado 1X2", "Empate"):                             p_draw,
        ("Resultado 1X2", "Visitante"):                          p_visit,
        ("Equipo que marca primero", "Local"):                   p_first_local,
        ("Equipo que marca primero", "Visitante"):               p_first_visit,
        ("Equipo que marca primero", "Sin gol"):                 p_no_gol,
        ("Ambos marcan (BTTS)", "Si"):                           p_btts_si,
        ("Ambos marcan (BTTS)", "No"):                           1 - p_btts_si,
        ("Total goles >2.5", "Si"):                              p_over25,
        ("Total goles >2.5", "No"):                              1 - p_over25,
        ("Goles totales Local", ">0.5"):                         goles_equipo(True, 1),
        ("Goles totales Local", ">1.5"):                         goles_equipo(True, 2),
        ("Goles totales Local", ">2.5"):                         goles_equipo(True, 3),
        ("Goles totales Visitante", ">0.5"):                     goles_equipo(False, 1),
        ("Goles totales Visitante", ">1.5"):                     goles_equipo(False, 2),
        ("Goles totales Visitante", ">2.5"):                     goles_equipo(False, 3),
        ("Cualquier equipo gana", "Local o Visitante (No empate)"): 1 - p_draw,
        ("Probabilidad total tarjetas", ">3.5 Si"):              p_tarj_si,
        ("Probabilidad total tarjetas", ">3.5 No"):              1 - p_tarj_si,
        ("Marcadores mas probables", f"Top 1: {top3[0][0]}"):   top3[0][1],
        ("Marcadores mas probables", f"Top 2: {top3[1][0]}"):   top3[1][1],
        ("Marcadores mas probables", f"Top 3: {top3[2][0]}"):   top3[2][1],
    }

@st.cache_data(ttl=3600)
def obtener_partidos_hoy():
    try:
        api_key = st.secrets["FOOTBALL_API_KEY"]
        hoy = datetime.now().strftime("%Y-%m-%d")
        url = f"https://api.football-data.org/v4/matches?date={hoy}"
        headers = {"X-Auth-Token": api_key}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        partidos = []
        for m in data.get("matches", []):
            estado = m.get("status", "")
            if estado not in ("SCHEDULED", "TIMED", "IN_PLAY"):
                continue
            local = m["homeTeam"]["name"]
            visit = m["awayTeam"]["name"]
            liga  = m.get("competition", {}).get("name", "Internacional")
            partidos.append({"local": local, "visit": visit, "liga": liga})
        return partidos
    except Exception:
        return []

def buscar_elo(nombre):
    nombre_lower = nombre.lower()
    for nombre_liga, equipos in LIGAS.items():
        for equipo, elo in equipos.items():
            if equipo.lower() in nombre_lower or nombre_lower in equipo.lower():
                return float(elo)
    return 1650.0

def generar_top5_partidos():
    seed = int(datetime.now().strftime("%Y%m%d"))
    random.seed(seed)
    ligas_disponibles = [l for l in LIGAS.keys() if l != "Copa Mundial 2026"]
    candidatos = []
    for nombre_liga in ligas_disponibles:
        equipos = list(LIGAS[nombre_liga].keys())
        if len(equipos) < 2:
            continue
        pares = [(equipos[i], equipos[j]) for i in range(len(equipos)) for j in range(i+1, len(equipos))]
        seleccionados = random.sample(pares, min(3, len(pares)))
        for loc, vis in seleccionados:
            elo_l = float(LIGAS[nombre_liga][loc])
            elo_v = float(LIGAS[nombre_liga][vis])
            gf_l2 = goles_favor(elo_l); gc_l2 = goles_contra(elo_l)
            gf_v2 = goles_favor(elo_v); gc_v2 = goles_contra(elo_v)
            lam2 = round((gf_l2 + gc_v2) / 2.0 * 1.05, 2)
            mu2  = round((gf_v2 + gc_l2) / 2.0 * 0.88, 2)
            p = calcular_probabilidades(elo_l, elo_v, 60.0, lam2, mu2, -0.05, 4.0)
            pl = p[("Resultado 1X2", "Local")]
            pe = p[("Resultado 1X2", "Empate")]
            pv = p[("Resultado 1X2", "Visitante")]
            mejor_prob = max(pl, pe, pv)
            if mejor_prob >= 0.50:
                candidatos.append({
                    "liga": nombre_liga, "local": loc, "visit": vis,
                    "p_local": pl, "p_empate": pe, "p_visit": pv,
                    "mejor_prob": mejor_prob,
                    "favorito": "LOCAL" if pl == mejor_prob else ("EMPATE" if pe == mejor_prob else "VISITANTE"),
                })
    candidatos.sort(key=lambda x: x["mejor_prob"], reverse=True)
    return candidatos[:5]

plan_actual = st.session_state.get("usuario_plan", "gratis")
limite_actual = LIMITES.get(plan_actual, 3)
if plan_actual != "pro":
    st.sidebar.info(f"Plan {plan_actual.upper()} — {limite_actual} pronosticos/dia")

if analizar and equipo_local != equipo_visit and not verificar_limite():
    st.error("Has alcanzado tu limite diario de pronosticos.")
    st.warning(f"Tienes el plan **{plan_actual.upper()}** ({limite_actual} pronosticos/dia).")
    st.markdown(f"### Quieres mas pronosticos?")
    col1, col2 = st.columns(2)
    col1.markdown("**Plan Basic — $5/mes**\n- 5 pronosticos por dia")
    col2.markdown("**Plan Pro — $10/mes**\n- Pronosticos ilimitados")
    st.link_button("Contactar por WhatsApp para suscribirte", WHATSAPP)
    st.stop()

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
    st.write(f"**Liga:** {liga}")

    p_loc = probs[("Resultado 1X2", "Local")]
    p_emp = probs[("Resultado 1X2", "Empate")]
    p_vis = probs[("Resultado 1X2", "Visitante")]

    st.markdown("### Resumen del resultado (1X2)")
    r1, r2, r3 = st.columns(3)
    r1.metric("LOCAL gana",      f"{p_loc * 100:.1f}%", f"Cuota justa {1/p_loc:.2f}")
    r2.metric("EMPATE",          f"{p_emp * 100:.1f}%", f"Cuota justa {1/p_emp:.2f}")
    r3.metric("VISITANTE gana",  f"{p_vis * 100:.1f}%", f"Cuota justa {1/p_vis:.2f}")

    favorito = max(
        [("LOCAL", p_loc), ("EMPATE", p_emp), ("VISITANTE", p_vis)],
        key=lambda t: t[1],
    )
    st.success(f"Resultado mas probable: {favorito[0]} ({favorito[1] * 100:.1f}%)")

    registrar_pronostico()
    st.markdown("### Cuadro final consolidado (todas las opciones)")
    st.dataframe(resultado, hide_index=True, use_container_width=True)
elif partidos_hoy:
    if not verificar_limite():
        st.error("Has alcanzado tu limite diario de pronosticos.")
        st.warning(f"Tienes el plan **{plan_actual.upper()}** ({limite_actual} pronosticos/dia).")
        st.link_button("Contactar por WhatsApp para suscribirte", WHATSAPP)
        st.stop()

    st.markdown("---")
    st.markdown(f"## TOP 5 PARTIDOS DE HOY — {datetime.now().strftime('%d/%m/%Y')}")

    with st.spinner("Obteniendo partidos de hoy..."):
        partidos = obtener_partidos_hoy()

    if not partidos:
        st.warning("No se encontraron partidos programados para hoy o hubo un error con la API.")
    else:
        candidatos = []
        for p in partidos:
            elo_l = buscar_elo(p["local"])
            elo_v = buscar_elo(p["visit"])
            gf_l2 = goles_favor(elo_l); gc_l2 = goles_contra(elo_l)
            gf_v2 = goles_favor(elo_v); gc_v2 = goles_contra(elo_v)
            lam2 = round((gf_l2 + gc_v2) / 2.0 * 1.05, 2)
            mu2  = round((gf_v2 + gc_l2) / 2.0 * 0.88, 2)
            pr = calcular_probabilidades(elo_l, elo_v, 60.0, lam2, mu2, -0.05, 4.0)
            pl = pr[("Resultado 1X2", "Local")]
            pe = pr[("Resultado 1X2", "Empate")]
            pv = pr[("Resultado 1X2", "Visitante")]
            mejor_prob = max(pl, pe, pv)
            candidatos.append({
                "liga": p["liga"], "local": p["local"], "visit": p["visit"],
                "p_local": pl, "p_empate": pe, "p_visit": pv,
                "mejor_prob": mejor_prob,
                "favorito": "LOCAL" if pl == mejor_prob else ("EMPATE" if pe == mejor_prob else "VISITANTE"),
            })
        candidatos.sort(key=lambda x: x["mejor_prob"], reverse=True)
        top5 = candidatos[:5]

        st.caption(f"Se encontraron {len(partidos)} partidos hoy. Mostrando los 5 con mayor probabilidad de resultado claro.")
        for i, m in enumerate(top5, 1):
            with st.container():
                st.markdown(f"### {i}. {m['local']} vs {m['visit']}")
                st.caption(f"Liga: {m['liga']}")
                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                c1.metric("LOCAL gana",     f"{m['p_local']*100:.1f}%")
                c2.metric("EMPATE",         f"{m['p_empate']*100:.1f}%")
                c3.metric("VISITANTE gana", f"{m['p_visit']*100:.1f}%")
                color = "green" if m["mejor_prob"] >= 0.60 else "orange"
                c4.markdown(f"**Favorito:** :{color}[{m['favorito']} ({m['mejor_prob']*100:.1f}%)]")
                st.info(f"Para analisis completo selecciona 'Otra liga (libre)' y escribe: **{m['local']}** vs **{m['visit']}**")
                st.markdown("---")
        registrar_pronostico()

elif mejores_hoy:
    if not verificar_limite():
        st.error("Has alcanzado tu limite diario de pronosticos.")
        st.warning(f"Tienes el plan **{plan_actual.upper()}** ({limite_actual} pronosticos/dia).")
        st.link_button("Contactar por WhatsApp para suscribirte", WHATSAPP)
        st.stop()

    st.markdown("---")
    st.markdown("## TOP 5 PARTIDOS RECOMENDADOS")
    st.info("Estos partidos son seleccionados por el modelo hibrido como los de mayor probabilidad de resultado claro. Verifica en tu casa de apuestas si se juegan hoy.")

    top5 = generar_top5_partidos()
    if not top5:
        st.warning("No se encontraron partidos con probabilidad suficiente. Intenta mas tarde.")
    else:
        for i, m in enumerate(top5, 1):
            with st.container():
                st.markdown(f"### {i}. {m['local']} vs {m['visit']}")
                st.caption(f"Liga: {m['liga']}")
                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                c1.metric("LOCAL gana",    f"{m['p_local']*100:.1f}%")
                c2.metric("EMPATE",        f"{m['p_empate']*100:.1f}%")
                c3.metric("VISITANTE gana",f"{m['p_visit']*100:.1f}%")
                color = "green" if m["mejor_prob"] >= 0.60 else "orange"
                c4.markdown(f"**Favorito:** :{color}[{m['favorito']} ({m['mejor_prob']*100:.1f}%)]")
                st.info(f"Para analisis completo: selecciona **{m['liga']}** en LIGA, pon **{m['local']}** como local y **{m['visit']}** como visitante, luego presiona ANALIZAR.")
                st.markdown("---")
    registrar_pronostico()
else:
    st.info("Elige liga y equipos, revisa los datos y presiona ANALIZAR en el menu lateral.")
