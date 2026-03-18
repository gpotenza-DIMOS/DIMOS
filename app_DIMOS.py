import streamlit as st
import os

# CONFIGURAZIONE PAGINA
st.set_page_config(page_title="DIMOS - Monitoring System", layout="wide")

# --- CSS PERSONALIZZATO PER RICALCARE IL TUO PRINT SCREEN ---
st.markdown("""
    <style>
        /* Sfondo sidebar scuro come da immagine */
        [data-testid="stSidebar"] {
            background-color: #262730;
            color: white;
        }
        /* Stile pulsanti nella sidebar */
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            height: 3em;
            background-color: #3e404a;
            color: white;
            border: 1px solid #555;
            transition: 0.3s;
            text-align: left;
            padding-left: 20px;
        }
        .stButton>button:hover {
            background-color: #50525d;
            border-color: #ff4b4b;
            color: white;
        }
        /* Rimuovi padding in eccesso sopra il logo */
        .block-container {
            padding-top: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DI AUTENTICAZIONE ---
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    
    if st.session_state["auth"]:
        return True

    # Schermata Login Centralizzata
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", use_container_width=True)
        st.markdown("<h3 style='text-align: center;'>Identificazione Utente</h3>", unsafe_allow_html=True)
        user = st.text_input("ID")
        pw = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            if user == "asdf" and pw == "asdf":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali Errate")
    return False

if check_password():
    # --- SIDEBAR CON PULSANTI COME DA IMMAGINE ---
    with st.sidebar:
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=80)
        
        st.markdown("### STRUMENTI")
        
        if st.button("🏠 Home Dashboard"):
            st.session_state["page"] = "home"
        
        if st.button("📏 Elettrolivelle"):
            st.session_state["page"] = "elettrolivelle"
            
        if st.button("📈 Grafici Monitoraggio"):
            st.session_state["page"] = "grafici"
        
        st.divider()
        if st.button("🚪 Esci"):
            st.session_state["auth"] = False
            st.rerun()

    # --- LOGICA DI NAVIGAZIONE ---
    attuale = st.session_state.get("page", "home")

    if attuale == "home":
        st.title("Piattaforma Integrata DIMOS")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.info("### Analisi Elettrolivelle")
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            if st.button("AVVIA MODULO LIVELLOMETRICO"):
                st.session_state["page"] = "elettrolivelle"
                st.rerun()

        with col_b:
            st.info("### Analisi Grafica / Stampe")
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("AVVIA MODULO GRAFICI"):
                st.session_state["page"] = "grafici"
                st.rerun()

    elif attuale == "elettrolivelle":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()

    elif attuale == "grafici":
        from plotter_mod import run_plotter
        run_plotter()
