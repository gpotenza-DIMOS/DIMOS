import streamlit as st
import os

# Configurazione Pagina
st.set_page_config(page_title="DIMOS - Monitoring System", layout="wide")

# Funzione per gestire l'accesso
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    if st.session_state["auth"]:
        return True

    # Schermata Login
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", use_container_width=True)
        
        st.subheader("🔑 Login di Accesso")
        user = st.text_input("ID")
        pw = st.text_input("Password", type="password")
        
        if st.button("Accedi", use_container_width=True):
            if user == "asdf" and pw == "asdf":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali errate")
    return False

if check_password():
    # Sidebar fissa con loghi
    with st.sidebar:
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=100)
        st.title("DIMOS Menu")
        scelta = st.radio("Navigazione:", ["Home Dashboard", "Elettrolivelle", "Grafici Monitoraggio"])
        st.divider()
        if st.button("Esci"):
            st.session_state["auth"] = False
            st.rerun()

    # LOGICA DASHBOARD INIZIALE
    if scelta == "Home Dashboard":
        st.title("Piattaforma Integrata DIMOS")
        st.write("Seleziona lo strumento di calcolo desiderato:")
        st.markdown("<br>", unsafe_allow_html=True)

        col_el, col_pl = st.columns(2)

        with col_el:
            st.subheader("📏 Modulo Elettrolivelle")
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            if st.button("Apri Calcolo Elettrolivelle", use_container_width=True):
                st.session_state["scelta_nav"] = "Elettrolivelle"
                # Forza il cambio stato per la navigazione
                st.rerun()

        with col_pl:
            st.subheader("📈 Grafici e Stampe")
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("Apri Gestione Grafici", use_container_width=True):
                st.session_state["scelta_nav"] = "Grafici Monitoraggio"
                st.rerun()

    # Navigazione verso i moduli
    # Gestione dello stato se cliccato dai bottoni della dashboard
    nav = st.session_state.get("scelta_nav", scelta)

    if nav == "Elettrolivelle":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()
    elif nav == "Grafici Monitoraggio":
        from plotter_mod import run_plotter
        run_plotter()
