import streamlit as st
import os
import plotter_mod  # Importiamo il tuo modulo plotter

# --- CONFIGURAZIONE PAGINA (UNICA CHIAMATA CONSENTITA) ---
st.set_page_config(
    page_title="DIMOS - Monitoraggio Strutturale", 
    layout="wide", 
    page_icon="📊"
)

# --- SISTEMA DI AUTENTICAZIONE ---
def check_password():
    """Ritorna True se la password è corretta."""
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    
    if st.session_state["auth"]:
        return True

    # Interfaccia di Login
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", width=400)
        
        st.title("Accesso Piattaforma DIMOS")
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Accedi"):
            # Modifica qui le tue credenziali
            if user == "admin" and password == "dimos2024":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali non valide")
    return False

# --- LOGICA PRINCIPALE ---
if check_password():
    # BARRA LATERALE DI NAVIGAZIONE
    with st.sidebar:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", width=200)
        st.title("Menu Principale")
        scelta = st.radio(
            "Seleziona Funzionalità:",
            ["🏠 Home Page", "📊 Visual & Plotter", "📂 Gestione Archivi"]
        )
        st.divider()
        if st.button("Logout"):
            st.session_state["auth"] = False
            st.rerun()

    # --- ROUTING DELLE PAGINE ---
    if scelta == "🏠 Home Page":
        st.title("Benvenuto nel Sistema DIMOS")
        st.write("Seleziona **Visual & Plotter** dal menu a sinistra per caricare i dati e iniziare l'analisi strutturale.")
        
        # Spiegazione Filtri
        with st.expander("Informazioni sull'Analisi di Gauss"):
            st.write("""
            Il sistema applica automaticamente un filtro basato sulla distribuzione normale (Gaussiana). 
            I dati che si discostano eccessivamente dalla media (outliers) vengono identificati e rimossi 
            per garantire una lettura pulita dei grafici.
            """)
            

[Image of normal distribution curve with standard deviation intervals]


    elif scelta == "📊 Visual & Plotter":
        # CHIAMATA AL MODULO ESTERNO
        # Assicurati che plotter_mod.py abbia la funzione run_plotter() 
        # e che NON contenga st.set_page_config
        plotter_mod.run_plotter()

    elif scelta == "📂 Gestione Archivi":
        st.subheader("Archivio Storico")
        st.info("Funzionalità in fase di implementazione.")
