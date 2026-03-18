import streamlit as st
import os

# 1. Configurazione - Deve essere la prima riga
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS "BRUTALE" PER COPIARE SCREEN1.JPG
st.markdown("""
    <style>
        /* Rimuove lo spazio bianco in alto alla sidebar e al corpo pagina */
        [data-testid="stSidebarContent"] {
            padding-top: 0rem !important;
            background-color: #1a1c23 !important;
        }
        .block-container {
            padding-top: 0rem !important;
        }
        header {visibility: hidden;}

        /* POSIZIONAMENTO LOGO CIRCOLARE (ANGOLO IN ALTO A SINISTRA) */
        .logo-box {
            display: flex;
            justify-content: flex-start;
            padding: 10px 0 20px 10px;
        }

        /* CONTAINER PULSANTI: ATTACCATI E SENZA SPAZI */
        .stButton button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 0px !important;
            padding: 15px 20px !important;
            text-align: left !important;
            margin: 0px !important; /* Elimina spazi tra bottoni */
            display: block !important;
            transition: all 0.2s ease-in-out !important;
            font-size: 14px !important;
            text-transform: uppercase !important;
        }

        /* HOVER: BORDO ROSSO A SINISTRA + TRANSLATE */
        .stButton button:hover {
            background-color: #3d4150 !important;
            border-left: 5px solid #ff4b4b !important;
            color: #ffffff !important;
            transform: translateX(2px) !important;
        }

        /* CLICK: EFFETTO BOTTONE PREMUTO */
        .stButton button:active {
            background-color: #1a1c23 !important;
            transform: translateY(2px) !important;
        }

        /* LOGO MICROGEO FISSO IN BASSO */
        .fixed-footer {
            position: fixed;
            bottom: 20px;
            width: 260px;
            background-color: #1a1c23;
            padding-bottom: 10px;
        }

        /* Nasconde la navigazione automatica di Streamlit */
        [data-testid="stSidebarNav"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN (ASDF / ASDF) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", use_container_width=True)
        with st.container(border=True):
            st.subheader("Login Accesso")
            u = st.text_input("ID")
            p = st.text_input("Password", type="password")
            if st.button("ACCEDI"):
                if u == "asdf" and p == "asdf":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else: st.error("Accesso negato")
    st.stop()

# --- SIDEBAR COSTRUITA COME DA SCREEN1.JPG ---
with st.sidebar:
    # Logo Circolare in alto a sinistra
    st.markdown('<div class="logo-box">', unsafe_allow_html=True)
    if os.path.exists("logo_DIMOScircle.jpg"):
        st.image("logo_DIMOScircle.jpg", width=110)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Gruppo pulsanti (senza markdown intermedi per tenerli uniti)
    if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "livelle"
    if st.button("📈 GRAFICI & STAMPE"): st.session_state["page"] = "grafici"
    
    # Footer fisso
    st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", width=200)
    if st.button("🚪 LOGOUT"):
        st.session_state["authenticated"] = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- NAVIGAZIONE ---
pg = st.session_state.get("page", "home")

if pg == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Modulo Livellometrico")
        if os.path.exists("montita.jpg"): st.image("montita.jpg", use_container_width=True)
        if st.button("AVVIA ELETTROLIVELLE"):
            st.session_state["page"] = "livelle"
            st.rerun()
    with c2:
        st.subheader("Grafici e Stampe")
        if os.path.exists("image_6e3d1e.jpg"): st.image("image_6e3d1e.jpg", use_container_width=True)
        if st.button("AVVIA MODULO GRAFICI"):
            st.session_state["page"] = "grafici"
            st.rerun()

elif pg == "livelle":
    from elettrolivelle_mod import run_elettrolivelle
    run_elettrolivelle()

elif pg == "grafici":
    from plotter_mod import run_plotter
    run_plotter()
