import streamlit as st
import os
import elettrolivelle_mod  # Assicurati che il file esista nella stessa cartella
import plotter_mod        # Assicurati che il file esista nella stessa cartella

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="DIMOS Platform", 
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (Sidebar Celeste e Stile Bottoni) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { 
        background-color: #B3CEE5; 
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: white;
        color: #31333F;
        border: 1px solid #d3d3d3;
        font-weight: 500;
        text-align: left;
        padding-left: 15px;
    }
    .stButton>button:hover {
        border: 1px solid #6495ED;
        color: #6495ED;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DI AUTENTICAZIONE ---
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    
    if st.session_state["auth"]:
        return True
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Accesso DIMOS</h2>", unsafe_allow_html=True)
        user_id = st.text_input("ID Utente")
        password = st.text_input("Password", type="password")
        if st.button("Entra"):
            if user_id == "asdf" and password == "asdf":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali errate.")
    return False

# --- LOGICA NAVIGAZIONE ---
def main():
    if check_password():
        if "pagina" not in st.session_state:
            st.session_state["pagina"] = "Home"

        # --- SIDEBAR ---
        with st.sidebar:
            if os.path.exists("logo_microgeo.jpg"):
                st.image("logo_microgeo.jpg", use_container_width=True)
            st.divider()
            
            # Mostra i pulsanti solo se non siamo in Home, oppure gestisci la navigazione
            if st.session_state["pagina"] == "Home":
                st.subheader("Moduli Disponibili")
                if st.button("📏 Elettrolivelle"): 
                    st.session_state["pagina"] = "Elettrolivelle"
                    st.rerun()
                if st.button("📈 VISUAL & PLOTTER"): 
                    st.session_state["pagina"] = "Plotter"
                    st.rerun()
                if st.button("🚧 Paratie"): 
                    st.session_state["pagina"] = "Paratie"
                    st.rerun()
                if st.button("🌉 Ponti"): 
                    st.session_state["pagina"] = "Ponti"
                    st.rerun()
                if st.button("🏢 Edifici"): 
                    st.session_state["pagina"] = "Edifici"
                    st.rerun()
            else:
                # Pulsante per tornare indietro se siamo dentro un modulo
                if st.button("🔙 Torna alla Home"):
                    st.session_state["pagina"] = "Home"
                    st.rerun()
            
            st.divider()
            if st.button("🚪 Logout"):
                st.session_state["auth"] = False
                st.rerun()

        # --- ROUTING CONTENUTO CENTRALE ---
        
        # 1. HOME PAGE
        if st.session_state["pagina"] == "Home":
            st.markdown("<br><br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 1, 1])
            with c2:
                if os.path.exists("logo_DIMOScircle.jpg"):
                    st.image("logo_DIMOScircle.jpg", width=500)
                elif os.path.exists("logo_dimos.jpg"):
                    st.image("logo_dimos.jpg", width=500)
            
            st.markdown("<h1 style='text-align: center;'>Piattaforma di Monitoraggio Integrata</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Gestione sensori, datalogger e analisi deformata.</p>", unsafe_allow_html=True)
        
        # 2. MODULO ELETTROLIVELLE
        elif st.session_state["pagina"] == "Elettrolivelle":
            try:
                elettrolivelle_mod.main() # Assicurati che elettrolivelle_mod.py abbia una def main()
            except AttributeError:
                st.error("Errore: Il modulo elettrolivelle non ha una funzione main().")

        # 3. MODULO PLOTTER (Corretto il nome rispetto al bottone)
        elif st.session_state["pagina"] == "Plotter":
            try:
                plotter_mod.main() # Chiama la funzione main() che gestisce i file caricati
            except AttributeError:
                st.error("Errore: Il modulo plotter non ha una funzione main().")
        
        # 4. ALTRI MODULI (Placeholder)
        elif st.session_state["pagina"] == "Paratie":
            st.title("🚧 Modulo Paratie")
            st.info("Sviluppo in corso per l'analisi delle paratie.")
            
        else:
            st.title(f"Modulo {st.session_state['pagina']}")
            st.warning("Sezione in fase di implementazione.")

# Avvio dell'applicazione
if __name__ == "__main__":
    main()
