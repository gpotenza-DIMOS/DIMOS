import streamlit as st
import os

# Configurazione 
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# CSS integrale (mantenuto il tuo stile originale)
st.markdown("""
    <style>
        [data-testid="stSidebarContent"] { background-color: #1a1c23 !important; padding-top: 0px !important; }
        [data-testid="stSidebarContent"] .stText, [data-testid="stSidebarContent"] label, 
        [data-testid="stSidebarContent"] h1, [data-testid="stSidebarContent"] h2, 
        [data-testid="stSidebarContent"] h3, [data-testid="stSidebarContent"] p { color: #e0e0e0 !important; }
        div.stButton > button {
            width: 100% !important; background-color: #2d303d !important; color: #ffffff !important;
            border: 1px solid #58607e !important; border-radius: 0px !important;
            text-align: left !important; padding: 15px 20px !important; margin: 0px !important;
        }
        div.stButton > button:hover { border-left: 8px solid #ff4b4b !important; background-color: #54533e !important; }
        header { visibility: hidden; }
        .block-container { padding-top: 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

if "auth" not in st.session_state: st.session_state["auth"] = False

if not st.session_state["auth"]:
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo_dimos.jpg"): st.image("logo_dimos.jpg")
        with st.container(border=True):
            u = st.text_input("ID")
            p = st.text_input("Password", type="password")
            if st.button("ACCEDI"):
                if u == "asdf" and p == "asdf":
                    st.session_state["auth"] = True
                    st.rerun()
                else: st.error("Credenziali Errate")
    st.stop()

# SIDEBAR: Navigazione Completa
with st.sidebar:
    if os.path.exists("logo_microgeo.jpg"): st.image("logo_microgeo.jpg", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
    if st.button("📈 ANALISI GRAFICA"): st.session_state["page"] = "pl"
    if st.button("📍 MAPPA & STRUTTURE"): st.session_state["page"] = "map"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "el"
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"):
        st.session_state["auth"] = False
        st.rerun()

pg = st.session_state.get("page", "home")

if pg == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()
    col_img1, col_img2 = st.columns([1, 4])
    with col_img1:
        if os.path.exists("logo_DIMOScircle.jpg"): st.image("logo_DIMOScircle.jpg", width=250)
    with col_img2:
        if os.path.exists("montita.jpg"): st.image("montita.jpg", width=400)
    
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("#### Grafici e Report")
            if st.button("Vai a GRAFICI", key="btn_pl"): st.session_state["page"] = "pl"; st.rerun()
    with c2:
        with st.container(border=True):
            st.markdown("#### Mappa Sensori")
            if st.button("Vai a MAPPA", key="btn_map"): st.session_state["page"] = "map"; st.rerun()
    with c3:
        with st.container(border=True):
            st.markdown("#### Elettrolivelle")
            if st.button("Vai a ELETTROLIVELLE", key="btn_el"): st.session_state["page"] = "el"; st.rerun()

elif pg == "pl":
    import plotter_mod
    plotter_mod.run_plotter()
elif pg == "map":
    import map_module
    map_module.run_map_manager()
elif pg == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()
elif pg == "el":
    import TPS_mod
    TPS_mod.run_TPS()
