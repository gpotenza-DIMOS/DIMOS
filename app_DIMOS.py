import streamlit as st
import os

# 1. Configurazione Pagina (L'unica ammessa in tutto il progetto)
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS "BRUTALE" PER COPIARE SCREEN1.JPG
st.markdown("""
    <style>
        /* Rimuove TUTTI i margini della sidebar */
        [data-testid="stSidebarContent"] {
            background-color: #1a1c23 !important;
            padding: 0rem !important;
        }
        
        /* Forza il Logo Microgeo nell'angolo in alto a sinistra senza spazi */
        .microgeo-header {
            width: 100%;
            padding: 0px !important;
            margin-top: -60px; /* Sale sopra il margine standard */
            margin-left: -5px;
        }

        /* Pulsanti Sidebar: Rettangolari e incollati */
        div.stButton > button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 0px !important;
            text-align: left !important;
            padding: 15px 20px !important;
            margin: 0px !important;
            transition: 0.2s;
        }

        /* Hover animato con linea rossa */
        div.stButton > button:hover {
            border-left: 5px solid #ff4b4b !important;
            background-color: #3d4150 !important;
            padding-left: 25px !important;
        }

        /* Card Home moderna */
        .home-card {
            border: 1px solid #ddd;
            border-radius: 12px;
            padding: 15px;
            background: #ffffff;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* Nasconde elementi Streamlit */
        header { visibility: hidden; }
        .block-container { padding-top: 0rem !important; }
        [data-testid="stSidebarNav"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg")
        with st.container(border=True):
            st.subheader("Login Accesso")
            u = st.text_input("ID")
            p = st.text_input("Password", type="password")
            if st.button("ACCEDI"):
                if u == "asdf" and p == "asdf":
                    st.session_state["auth"] = True
                    st.rerun()
                else: st.error("Accesso negato")
    st.stop()

# --- SIDEBAR: LOGO MICROGEO IN ALTO A SINISTRA ---
with st.sidebar:
    st.markdown('<div class="microgeo-header">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Pulsanti Menu
    if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "el"
    if st.button("📈 GRAFICI & STAMPE"): st.session_state["page"] = "pl"
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"):
        st.session_state["auth"] = False
        st.rerun()

# --- CONTENUTO PRINCIPALE ---
pg = st.session_state.get("page", "home")

if pg == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            # Header card: Logo Circle + Titolo
            h1, h2 = st.columns([1, 4])
            with h1:
                if os.path.exists("logo_DIMOScircle.jpg"):
                    st.image("logo_DIMOScircle.jpg", width=80)
            with h2:
                st.markdown("### Modulo Elettrolivelle")
            
            # Immagine Montita
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            
            if st.button("AVVIA MODULO LIVELLOMETRICO"):
                st.session_state["page"] = "el"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("### Monitoraggio Grafici")
            # Immagine grafico
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("AVVIA MODULO GRAFICI"):
                st.session_state["page"] = "pl"
                st.rerun()

# --- CARICAMENTO MODULI ESTERNI ---
elif pg == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()

elif pg == "pl":
    import plotter_mod
    plotter_mod.run_plotter()
