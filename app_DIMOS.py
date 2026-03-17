import streamlit as st
# Importiamo i moduli dalle altre cartelle/file
import elettrolivelle_mod 

# --- NAVIGAZIONE ---
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "Home"

def navigation():
    with st.sidebar:
        st.image("logo_microgeo.jpg")
        if st.session_state["pagina"] == "Home":
            st.markdown("### Menu Applicazioni")
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

# --- LOGICA DI CARICAMENTO ---
navigation()

if st.session_state["pagina"] == "Home":
    st.image("logo_dimos.jpg")
    st.title("Piattaforma DIMOS")
    st.write("Seleziona un'applicazione dalla sidebar.")

elif st.session_state["pagina"] == "Elettrolivelle":
    # Qui chiamiamo il file esterno!
    elettrolivelle_mod.run_elettrolivelle()

elif st.session_state["pagina"] == "Paratie":
    st.title("Modulo Paratie")
    st.write("Contenuto caricato dal file paratie.py")
