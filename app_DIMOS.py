import streamlit as st
import os

# 1. Configurazione Pagina
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS "HARD" PER POSIZIONAMENTO MILLIMETRICO
st.markdown("""
    <style>
        /* Sfondo Sidebar e rimozione padding superiore */
        [data-testid="stSidebarContent"] {
            background-color: #1a1c23 !important;
            padding-top: 0rem !important;
        }
        .block-container { padding-top: 0rem !important; }
        header { visibility: hidden; }

        /* LOGO MICROGEO IN ALTO A SINISTRA NELLA SIDEBAR */
        .sidebar-logo {
            padding: 10px 0 10px 10px;
            margin-top: -30px;
        }

        /* PULSANTI SIDEBAR: COMPATTI E REATTIVI */
        .stButton button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 0px !important;
            padding: 12px 15px !important;
            text-align: left !important;
            margin-bottom: -1px !important;
            transition: all 0.2s ease-in-out;
        }
        .stButton button:hover {
            background-color: #3d4150 !important;
            border-left: 5px solid #ff4b4b !important;
            transform: translateX(3px);
        }

        /* CARD HOME: COMBINAZIONE LOGO CIRCLE + MONTITA */
        .home-container {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 0px;
            overflow: hidden;
            max-width: 500px;
        }
        .header-box {
            display: flex;
            align-items: center;
            padding: 10px;
            background: #f8f9fa;
        }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN (Come richiesto) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with col2 := c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", use_container_width=True)
        with st.container(border=True):
            st.subheader("Login Accesso")
            u = st.text_input("ID", key="user")
            p = st.text_input("Password", type="password", key="pass")
            if st.button("ACCEDI"):
                if u == "asdf" and p == "asdf":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else: st.error("Accesso negato")
    st.stop()

# --- SIDEBAR: LOGO MICROGEO + PULSANTI ---
with st.sidebar:
    st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", width=220)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Pulsanti Menu
    if st.button("🏠 HOME DASHBOARD"): st.session_state["pg"] = "home"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["pg"] = "el"
    if st.button("📈 GRAFICI & STAMPE"): st.session_state["pg"] = "pl"
    
    # Spazio e Logout
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- CONTENUTO PRINCIPALE ---
pg = st.session_state.get("pg", "home")

if pg == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        # CONTENITORE COMBINATO PER ELETTROLIVELLE
        st.markdown("""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; background:#fff;">
                <div style="display:flex; align-items:center; margin-bottom:15px;">
                    <img src="https://via.placeholder.com/60" id="circle_ph" style="width:60px; margin-right:15px;">
                    <h3 style="margin:0;">Modulo Elettrolivelle</h3>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Inserimento immagini reali sopra il blocco HTML via Streamlit per stabilità
        inner1, inner2 = st.columns([1, 4])
        with inner1:
            if os.path.exists("logo_DIMOScircle.jpg"):
                st.image("logo_DIMOScircle.jpg", width=70)
        with inner2:
            st.markdown("### Calcolo Livelle")
        
        if os.path.exists("montita.jpg"):
            st.image("montita.jpg", use_container_width=True)
            
        if st.button("APRI MODULO LIVELLOMETRICO", key="go_el"):
            st.session_state["pg"] = "el"
            st.rerun()

    with col_b:
        # CONTENITORE PER GRAFICI
        with st.container(border=True):
            st.markdown("### Grafici e Reportistica")
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            else:
                st.info("Area per caricamento dati e stampe")
            
            if st.button("APRI MODULO GRAFICI", key="go_pl"):
                st.session_state["pg"] = "pl"
                st.rerun()

elif pg == "el":
    from elettrolivelle_mod import run_elettrolivelle
    run_elettrolivelle()

elif pg == "pl":
    from plotter_mod import run_plotter
    run_plotter()
