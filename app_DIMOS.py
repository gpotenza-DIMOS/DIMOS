import streamlit as st
import os
import elettrolivelle_mod  # Importa il modulo esterno per l'elaborazione

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS Platform", layout="wide")

# --- CUSTOM CSS (Colore sidebar celeste e stile bottoni) ---
st.markdown("""
    <style>
    /* Colore celeste sidebar come richiesto */
    [data-testid="stSidebar"] { 
        background-color: #B3CEE5; 
    }
    /* Stile per i bottoni del menu */
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
            if user_id == "dimos" and password == "micai!":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali errate.")
    return False

# --- LOGICA APPLICATIVA ---
if check_password():
    # Stato della navigazione
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "Home"

    # Sidebar Dinamica
    with st.sidebar:
        if os.path.exists("logo_microgeo.jpg"):
            st.image("logo_microgeo.jpg", use_container_width=True)
        st.divider()
        
        # Mostra il menu solo se siamo in Home
        if st.session_state["pagina"] == "Home":
            st.subheader("Moduli Disponibili")
            if st.button("📏 Elettrolivelle"): 
                st.session_state["pagina"] = "Elettrolivelle"
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
            if st.button("📉 PLOTTER"): 
                st.session_state["pagina"] = "Plotter"
                st.rerun()
        else:
            # Se siamo dentro un modulo, mostra il tasto per tornare indietro
            if st.button("🔙 Torna alla Home"):
                st.session_state["pagina"] = "Home"
                st.rerun()
        
        st.divider()
        if st.button("🚪 Logout"):
            st.session_state["auth"] = False
            st.rerun()

    # --- CONTENUTO CENTRALE (DASHBOARD) ---
    if st.session_state["pagina"] == "Home":
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Layout a tre colonne per centrare il logo scalato
        c1, c2, c3 = st.columns([1, 1, 1]) 
        with c2:
            # Logo circolare caricato e scalato (dimensione circa la metà)
            if os.path.exists("logo_DIMOScircle.jpg"):
                st.image("logo_DIMOScircle.jpg", width=350) 
            else:
                st.image("logo_dimos.jpg", width=350)
        
        st.markdown("<h1 style='text-align: center;'>Piattaforma di Monitoraggio Integrata</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Seleziona un'applicazione dalla barra laterale celeste per iniziare.</p>", unsafe_allow_html=True)
    
    # --- CARICAMENTO MODULI ESTERNI ---
    elif st.session_state["pagina"] == "Elettrolivelle":
        # Richiama l'algoritmo completo dal file elettrolivelle_mod.py
        elettrolivelle_mod.run_elettrolivelle()
    
    elif st.session_state["pagina"] == "Paratie":
        st.title("🚧 Modulo Paratie")
        st.info("Area in fase di configurazione. Caricare il modulo paratie_mod.py per attivare le funzioni.")
    
    else:
        st.title(f"Modulo {st.session_state['pagina']}")
        st.warning("Questa sezione sarà disponibile con i prossimi aggiornamenti.")
