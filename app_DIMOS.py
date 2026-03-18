import streamlit as st
import os

# 1. Configurazione Iniziale
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS per ricalcare fedelmente lo screenshot e le tue richieste
st.markdown("""
    <style>
        /* Sfondo Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1a1c23 !important;
        }
        
        /* Rimuove spazi bianchi in alto */
        .block-container { padding-top: 1rem !important; }
        header { visibility: hidden; }

        /* Stile Pulsanti Sidebar (Grigi, rettangolari, animati) */
        .stButton button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 4px !important;
            padding: 12px 15px !important;
            text-align: left !important;
            margin-bottom: 5px !important;
            transition: all 0.3s ease;
        }
        
        /* Effetto Hover Pulsanti */
        .stButton button:hover {
            border-left: 5px solid #ff4b4b !important;
            background-color: #3d4150 !important;
            transform: translateX(5px);
        }

        /* Stile per la "Card" Home (Immagini combinate) */
        .home-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #ddd;
            text-align: center;
            box-shadow: 2px 2px 15px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONE LOGIN (Esattamente come da screenshot) ---
def login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if os.path.exists("logo_dimos.jpg"):
                st.image("logo_dimos.jpg", use_container_width=True)
            
            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>Accesso al Sistema</h3>", unsafe_allow_html=True)
                u = st.text_input("ID Utente")
                p = st.text_input("Password", type="password")
                if st.button("ACCEDI AL PORTALE"):
                    if u == "asdf" and p == "asdf":
                        st.session_state["authenticated"] = True
                        st.rerun()
                    else:
                        st.error("Credenziali Errate")
        return False
    return True

# --- LOGICA APPLICAZIONE ---
if login():
    # BARRA LATERALE: Logo Microgeo in alto e Menu
    with st.sidebar:
        if os.path.exists("logo_microgeo.jpg"):
            st.image("logo_microgeo.jpg", use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏠 HOME DASHBOARD"): st.session_state["pg"] = "home"
        if st.button("📏 ELETTROLIVELLE"): st.session_state["pg"] = "el"
        if st.button("📈 GRAFICI & STAMPE"): st.session_state["pg"] = "pl"
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 ESCI"):
            st.session_state["authenticated"] = False
            st.rerun()

    # CONTENUTO PRINCIPALE
    pg = st.session_state.get("pg", "home")

    if pg == "home":
        st.title("Piattaforma DIMOS - Pannello Controllo")
        st.divider()
        
        # Impaginazione Home con combinazione immagini
        c1, c2 = st.columns(2)
        
        with c1:
            with st.container(border=True):
                # Combinazione Logo Circle + Montita
                col_sub1, col_sub2 = st.columns([1, 2])
                with col_sub1:
                    if os.path.exists("logo_DIMOScircle.jpg"):
                        st.image("logo_DIMOScircle.jpg", width=100)
                with col_sub2:
                    st.markdown("#### Modulo Elettrolivelle")
                
                if os.path.exists("montita.jpg"):
                    st.image("montita.jpg", use_container_width=True)
                
                if st.button("APRI APPLICAZIONE LIVELLOMETRICA"):
                    st.session_state["pg"] = "el"
                    st.rerun()

        with c2:
            with st.container(border=True):
                st.markdown("#### Modulo Grafici Monitoraggio")
                # Qui puoi mettere l'immagine dei grafici
                if os.path.exists("image_6e3d1e.jpg"):
                    st.image("image_6e3d1e.jpg", use_container_width=True)
                else:
                    st.info("Area Grafici e Stampe")
                
                if st.button("APRI APPLICAZIONE GRAFICI"):
                    st.session_state["pg"] = "pl"
                    st.rerun()

    elif pg == "el":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()

    elif pg == "pl":
        from plotter_mod import run_plotter
        run_plotter()
