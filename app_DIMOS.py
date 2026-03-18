import streamlit as st
import os
import plotter_mod

# UNICA CONFIGURAZIONE CONSENTITA
st.set_page_config(page_title="DIMOS - Monitoraggio", layout="wide")

def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    if st.session_state["auth"]:
        return True

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", width=400)
        st.title("Accesso Piattaforma DIMOS")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Entra"):
            if user == "asdf" and pw == "asdf":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali errate")
    return False

if check_password():
    with st.sidebar:
        st.image("logo_dimos.jpg", width=200)
        st.title("Menu")
        scelta = st.radio("Navigazione", ["🏠 Home", "📊 Visual & Plotter"])
        if st.button("Logout"):
            st.session_state["auth"] = False
            st.rerun()

    if scelta == "🏠 Home":
        st.title("Sistema di Monitoraggio Strutturale")
        st.info("Benvenuto. Vai nella sezione Visual & Plotter per analizzare i dati.")
    
    elif scelta == "📊 Visual & Plotter":
        plotter_mod.run_plotter()
