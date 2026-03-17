import streamlit as st
import elettrolivelle_mod  # Deve esistere questo file nel tuo GitHub

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS Platform", layout="wide")

# --- LOGIN (Ripristinato) ---
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    if st.session_state["auth"]:
        return True
    
    # Se non autenticato, mostra il form
    st.image("logo_dimos.jpg", width=300)
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
    # --- NAVIGAZIONE ---
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "Home"

    with st.sidebar:
        st.image("logo_microgeo.jpg", use_container_width=True)
        if st.session_state["pagina"] == "Home":
            if st.button("📏 Elettrolivelle"):
                st.session_state["pagina"] = "Elettrolivelle"
                st.rerun()
            if st.button("🚧 Paratie"):
                st.session_state["pagina"] = "Paratie"
                st.rerun()
        else:
            if st.button("🔙 Torna alla Home"):
                st.session_state["pagina"] = "Home"
                st.rerun()

    # --- LOGICA CARICAMENTO MODULI ---
    if st.session_state["pagina"] == "Home":
        st.title("Benvenuto in DIMOS")
        st.info("Seleziona un modulo dalla barra laterale.")
    
    elif st.session_state["pagina"] == "Elettrolivelle":
        # Questo comando cerca la funzione nel file elettrolivelle_mod.py
        elettrolivelle_mod.run_elettrolivelle()
