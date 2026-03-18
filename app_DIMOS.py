import streamlit as st
import os

# Configurazione obbligatoria (Solo qui!)
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# CSS "AGRESSIVO" 
st.markdown("""
    <style>
        /* 1. SIDEBAR: Rimuove ogni spazio in alto e imposta il colore */
        [data-testid="stSidebarContent"] {
            background-color: #1a1c23 !important;
            padding-top: 0px !important;
        }
        
        /* 2. LOGO MICROGEO: Lo spinge in alto nell'angolo */
        .microgeo-top {
            margin-top: -50px; /* Elimina il gap di Streamlit */
            margin-left: -10px;
            margin-bottom: 20px;
            display: block;
        }

        /* 3. PULSANTI SIDEBAR: Incollati, rettangolari, effetto metallo scuro */
        div.stButton > button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 0px !important; /* Rettangolari come screen1 */
            text-align: left !important;
            padding: 15px 20px !important;
            margin-bottom: -1px !important; /* Evita doppio bordo tra bottoni */
            font-size: 14px !important;
            transition: 0.2s;
        }
        
        /* Animazione Hover */
        div.stButton > button:hover {
            border-left: 5px solid #ff4b4b !important;
            background-color: #3d4150 !important;
            padding-left: 25px !important;
        }

        /* 4. HOME CARD: Combinazione Logo Circle + Montita */
        .home-card {
            border: 1px solid #ddd;
            border-radius: 10px;
            background: white;
            padding: 0px;
            overflow: hidden;
        }
        
        /* Pulizia generale pagina */
        header { visibility: hidden; }
        .block-container { padding-top: 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA LOGIN ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
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

# --- SIDEBAR (LOGO MICROGEO IN ALTO) ---
with st.sidebar:
    st.markdown('<div class="microgeo-top">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", width=250)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Pulsanti Menu
    if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "el"
    if st.button("📈 GRAFICI & STAMPE"): st.session_state["page"] = "pl"
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"):
        st.session_state["auth"] = False
        st.rerun()

# --- HOME PAGE (LOGO CIRCLE + MONTITA) ---
page = st.session_state.get("page", "home")

if page == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            # Header della card: Logo Circle + Titolo
            head1, head2 = st.columns([1, 4])
            with head1:
                if os.path.exists("logo_DIMOScircle.jpg"):
                    st.image("logo_DIMOScircle.jpg", width=70)
            with head2:
                st.markdown("### Modulo Livellometrico")
            
            # Immagine Montita
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            
            if st.button("AVVIA CALCOLO ELETTROLIVELLE"):
                st.session_state["page"] = "el"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("### Grafici e Report")
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("AVVIA MODULO PLOTTER"):
                st.session_state["page"] = "pl"
                st.rerun()

elif page == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()

elif page == "pl":
    import plotter_mod
    plotter_mod.run_plotter()
