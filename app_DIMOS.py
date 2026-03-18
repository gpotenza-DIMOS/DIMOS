import streamlit as st
import os

# CONFIGURAZIONE PAGINA (UNICA PER TUTTA L'APP)
st.set_page_config(page_title="DIMOS - Software Monitoraggio", layout="wide")

# IMPORTAZIONE MODULI
from elettrolivelle_mod import run_elettrolivelle
from plotter_mod import run_plotter

def check_password():
    """Ritorna True se le credenziali sono corrette"""
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    
    if st.session_state["auth"]:
        return True

    # Schermata di Login
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try:
            st.image("logo_dimos.jpg", use_container_width=True)
        except:
            st.title("DIMOS")
        
        st.subheader("🔐 Accesso Riservato")
        user = st.text_input("ID Utente")
        pw = st.text_input("Password", type="password")
        
        if st.button("Accedi"):
            # Qui puoi cambiare le tue credenziali
            if user == "admin" and pw == "dimos2024": 
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali non valide")
    return False

if check_password():
    # SIDEBAR COMUNE
    with st.sidebar:
        try:
            st.image("logo_microgeo.jpg", use_container_width=True)
        except:
            pass
        
        st.divider()
        scelta = st.radio(
            "Seleziona Strumento:",
            ["🏠 Home", "📏 Elettrolivelle", "📈 Monitoraggio - Stampe"]
        )
        st.divider()
        if st.button("Logout"):
            st.session_state["auth"] = False
            st.rerun()

    # LOGICA DI NAVIGAZIONE
    if scelta == "🏠 Home":
        st.title("Benvenuto nel Sistema DIMOS")
        st.write("Seleziona un modulo dal menu laterale per iniziare l'elaborazione.")
        st.info("I moduli caricano i dati da file Excel secondo gli standard definiti.")
        
    elif scelta == "📏 Elettrolivelle":
        run_elettrolivelle()
        
    elif scelta == "📈 Monitoraggio - Stampe":
        run_plotter()
