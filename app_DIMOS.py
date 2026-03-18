import streamlit as st
import os

# Configurazione Pagina
st.set_page_config(page_title="DIMOS - Sistema Integrato", layout="wide")

# --- CSS CUSTOM PER SIDEBAR E BOTTONI ---
st.markdown("""
    <style>
        /* Sfondo Sidebar scuro */
        [data-testid="stSidebar"] {
            background-color: #1E1E1E;
        }
        /* Stile pulsanti Sidebar */
        .stButton > button {
            width: 100%;
            border-radius: 0px;
            height: 3em;
            background-color: #333333;
            color: white;
            border: none;
            text-align: left;
            padding-left: 15px;
            margin-bottom: -10px;
        }
        .stButton > button:hover {
            background-color: #444444;
            border-left: 5px solid #ff4b4b;
            color: white;
        }
        /* Nasconde i margini standard */
        .block-container { padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN ---
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    if st.session_state["auth"]: return True

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", use_container_width=True)
        st.subheader("Login Accesso")
        u = st.text_input("ID")
        p = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            if u == "asdf" and p == "asdf":
                st.session_state["auth"] = True
                st.rerun()
            else: st.error("Accesso negato")
    return False

if check_password():
    # --- SIDEBAR STRUTTURATA ---
    with st.sidebar:
        # Logo in alto
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=100)
        
        st.markdown("<h2 style='color:white;'>STRUMENTI</h2>", unsafe_allow_html=True)
        
        # Pulsanti di navigazione
        if st.button("🏠 Home Dashboard"): st.session_state["pg"] = "home"
        if st.button("📏 Elettrolivelle"): st.session_state["pg"] = "el"
        if st.button("📈 Grafici Monitoraggio"): st.session_state["pg"] = "pl"
        
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        # Logo Microgeo in basso nella sidebar
        if os.path.exists("logo_microgeo.jpg"):
            st.image("logo_microgeo.jpg", use_container_width=True)
            
        if st.button("🚪 Esci"):
            st.session_state["auth"] = False
            st.rerun()

    # --- CONTENUTO ---
    pagina = st.session_state.get("pg", "home")

    if pagina == "home":
        st.title("Piattaforma DIMOS")
        c1, c2 = st.columns(2)
        with c1:
            if os.path.exists("montita.jpg"): st.image("montita.jpg", use_container_width=True)
            if st.button("APRI ELETTROLIVELLE", key="btn_el"):
                st.session_state["pg"] = "el"
                st.rerun()
        with c2:
            if os.path.exists("image_6e3d1e.jpg"): st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("APRI GRAFICI", key="btn_pl"):
                st.session_state["pg"] = "pl"
                st.rerun()

    elif pagina == "el":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()

    elif pagina == "pl":
        from plotter_mod import run_plotter
        run_plotter()
