import streamlit as st
import os

# Configurazione Pagina (L'unica nel progetto)
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# --- SCREEN ---
st.markdown("""
    <style>
        /* Sidebar: Sfondo scuro e rimozione spazi bianchi in alto */
        [data-testid="stSidebarContent"] {
            background-color: #1a1c23 !important;
            padding: 0px !important;
        }
        .block-container { padding-top: 0rem !important; }
        header { visibility: hidden; }

        /* Posizionamento Logo Microgeo nell'angolo estremo */
        .microgeo-box {
            margin-top: -50px; 
            margin-left: -5px;
            padding: 10px;
        }

        /* Pulsanti Sidebar: Grigio scuro, quadrati, attaccati */
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
            text-transform: uppercase;
            font-size: 13px;
        }

        /* Hover Pulsanti: Linea rossa a sinistra */
        div.stButton > button:hover {
            border-left: 5px solid #ff4b4b !important;
            background-color: #3d4150 !important;
            padding-left: 25px !important;
        }

        /* Box Home: Layout Logo Circle + Titolo */
        .home-header-box {
            display: flex;
            align-items: center;
            background-color: #f8f9fa;
            padding: 15px;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 10px 10px 0 0;
        }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN (Invariato come richiesto) ---
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

# --- SIDEBAR: LOGO MICROGEO + MENU ---
with st.sidebar:
    st.markdown('<div class="microgeo-box">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Pulsanti incollati tra loro
    if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "el"
    if st.button("📈 GRAFICI & STAMPE"): st.session_state["page"] = "pl"
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 ESCI"):
        st.session_state["auth"] = False
        st.rerun()

# --- CONTENUTO PRINCIPALE ---
pg = st.session_state.get("page", "home")

if pg == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Card Elettrolivelle: Logo Circle e Titolo affiancati
        with st.container(border=True):
            sub_c1, sub_c2 = st.columns([1, 4])
            with sub_c1:
                if os.path.exists("logo_DIMOScircle.jpg"):
                    st.image("logo_DIMOScircle.jpg", width=80)
            with sub_c2:
                st.markdown("### Modulo Elettrolivelle")
            
            # Foto Montita grande
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            
            if st.button("AVVIA MODULO LIVELLOMETRICO"):
                st.session_state["page"] = "el"
                st.rerun()

    with col_right:
        # Card Grafici
        with st.container(border=True):
            st.markdown("### Grafici e Stampe")
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("AVVIA MODULO GRAFICI"):
                st.session_state["page"] = "pl"
                st.rerun()

# --- CARICAMENTO MODULI ---
elif pg == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()

elif pg == "pl":
    import plotter_mod
    plotter_mod.run_plotter()
