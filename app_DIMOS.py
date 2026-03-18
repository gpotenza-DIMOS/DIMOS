import streamlit as st
import os

# 1. Configurazione - Wide mode obbligatoria
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS "CHIRURGICO" PER COPIARE SCREEN1.JPG
st.markdown("""
    <style>
        /* Rimuove lo spazio bianco in cima alla sidebar */
        [data-testid="stSidebarContent"] {
            background-color: #1a1c23 !important;
            padding-top: 0px !important;
        }
        
        /* Forza il Logo Microgeo nell'angolo in alto a sinistra (Top-Left) */
        .microgeo-top {
            position: absolute;
            top: -55px;
            left: -10px;
            width: 250px;
            z-index: 1000;
        }

        /* Pulsanti Sidebar: Grigio scuro, quadrati, senza spazio tra loro */
        div.stButton > button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 0px !important;
            text-align: left !important;
            padding: 15px 20px !important;
            margin: 0px !important;
            font-size: 14px !important;
            display: block !important;
        }

        /* Effetto Hover: Riga rossa laterale */
        div.stButton > button:hover {
            border-left: 5px solid #ff4b4b !important;
            background-color: #3d4150 !important;
        }

        /* Stile per la Card Home (Logo Circle + Titolo) */
        .header-container {
            display: flex;
            align-items: center;
            background: #f8f9fa;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px 8px 0 0;
        }

        /* Nasconde header Streamlit e riduce padding pagina */
        header { visibility: hidden; }
        .block-container { padding-top: 0rem !important; }
        [data-testid="stSidebarNav"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA LOGIN ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    _, col_login, _ = st.columns([1, 1, 1])
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
                else: st.error("Credenziali Errate")
    st.stop()

# --- SIDEBAR (POSIZIONAMENTO FISSO) ---
with st.sidebar:
    # Div HTML per forzare il logo in alto a sx
    st.markdown(f'<div class="microgeo-top">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br><br><br>", unsafe_allow_html=True) # Spazio per non coprire il logo
    
    # Pulsanti Menu
    if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "el"
    if st.button("📈 GRAFICI & STAMPE"): st.session_state["page"] = "pl"
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"):
        st.session_state["auth"] = False
        st.rerun()

# --- CONTENUTO PRINCIPALE ---
page = st.session_state.get("page", "home")

if page == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            # Layout: Logo Circle a sinistra, Titolo a destra
            h1, h2 = st.columns([1, 4])
            with h1:
                if os.path.exists("logo_DIMOScircle.jpg"):
                    st.image("logo_DIMOScircle.jpg", width=80)
            with h2:
                st.markdown("### Modulo Elettrolivelle")
            
            # Immagine Montita grande sotto
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            
            if st.button("APRI APPLICAZIONE"):
                st.session_state["page"] = "el"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("### Grafici e Reportistica")
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("APRI MODULO GRAFICI"):
                st.session_state["page"] = "pl"
                st.rerun()

# --- CARICAMENTO MODULI (Senza set_page_config interno!) ---
elif page == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()

elif page == "pl":
    import plotter_mod
    plotter_mod.run_plotter()
