import streamlit as st
import os
from elettrolivelle_mod import run_elettrolivelle
from plotter_mod import run_plotter

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Sistema Integrato", layout="wide")

def get_asset_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

# --- SISTEMA DI AUTENTICAZIONE ---
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    if st.session_state["auth"]:
        return True
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        p_logo = get_asset_path("logo_dimos.jpg")
        if os.path.exists(p_logo):
            st.image(p_logo, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Accesso DIMOS</h2>", unsafe_allow_html=True)
        user_id = st.text_input("ID Utente")
        password = st.text_input("Password", type="password")
        if st.button("Entra"):
            if user_id == "dimos" and password == "micai!":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali errate")
    return False

if check_password():
    # Sidebar comune
    with st.sidebar:
        p_side = get_asset_path("logo_microgeo.jpg")
        if os.path.exists(p_side):
            st.image(p_side, use_container_width=True)
        
        st.divider()
        scelta = st.radio("Seleziona Strumento:", 
                         ["🏠 Home", "📏 Elettrolivelle", "📈 Monitoraggio - Stampe"])
        
        st.divider()
        if st.button("Esci"):
            st.session_state["auth"] = False
            st.rerun()

    # Navigazione
    if scelta == "🏠 Home":
        st.title("Benvenuto nel Sistema DIMOS")
        st.image(get_asset_path("logo_dimos.jpg"), width=500)
        st.info("Seleziona uno strumento dalla barra laterale per iniziare.")
        
    elif scelta == "📏 Elettrolivelle":
        run_elettrolivelle()
        
    elif scelta == "📈 Monitoraggio - Stampe":
        run_plotter()
