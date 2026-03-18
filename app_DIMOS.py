import streamlit as st
import os

# Configurazione Pagina (Deve essere la prima)
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# --- CSS DEFINITIVO PER COPIARE SCREEN1.JPG ---
st.markdown("""
    <style>
        /* Sfondo sidebar scuro come software desktop */
        [data-testid="stSidebar"] {
            background-color: #1a1c23 !important;
        }

        /* Posizionamento estremo logo circolare in alto a sx */
        .logo-container {
            position: absolute;
            top: -60px;
            left: -15px;
            z-index: 999;
        }

        /* Contenitore pulsanti senza spazi intermedi */
        .stButton button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 0px !important; /* Angoli vivi per effetto blocco */
            padding: 12px 20px !important;
            text-align: left !important;
            margin-bottom: -1px !important; /* Sovrappone i bordi per non raddoppiarli */
            transition: all 0.2s ease-in-out !important;
            font-size: 14px !important;
            text-transform: uppercase !important;
        }

        /* Animazione Hover: si accende di rosso a sinistra */
        .stButton button:hover {
            background-color: #3d4150 !important;
            border-left: 4px solid #ff4b4b !important;
            padding-left: 21px !important; /* Compensa il bordo */
        }

        /* Effetto Click Realistico */
        .stButton button:active {
            background-color: #111217 !important;
            transform: scale(0.98) !important;
        }

        /* Logo Microgeo fisso in fondo alla sidebar */
        .sidebar-footer {
            position: fixed;
            bottom: 15px;
            left: 15px;
            width: 250px;
        }

        /* Pulizia interfaccia Streamlit */
        header {visibility: hidden;}
        [data-testid="stSidebarNav"] {display: none;}
        .block-container {padding-top: 0rem;}
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN (Invariato, ID/PW: asdf) ---
def check_login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if os.path.exists("logo_dimos.jpg"):
                st.image("logo_dimos.jpg", use_container_width=True)
            st.subheader("Login Accesso")
            uid = st.text_input("ID")
            psw = st.text_input("Password", type="password")
            if st.button("ACCEDI"):
                if uid == "asdf" and psw == "asdf":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else: st.error("Credenziali Errate")
        return False
    return True

if check_login():
    # SIDEBAR - COSTRUZIONE ESATTA DA SCREEN1.JPG
    with st.sidebar:
        # Logo Circolare
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=100)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br><br><br>", unsafe_allow_html=True) # Spazio per il logo fluttuante
        
        # Blocco Pulsanti
        if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
        if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "livelle"
        if st.button("📈 GRAFICI & STAMPE"): st.session_state["page"] = "grafici"
        
        # Footer con Microgeo
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        if os.path.exists("logo_microgeo.jpg"):
            st.image("logo_microgeo.jpg", width=200)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 LOGOUT"):
            st.session_state["authenticated"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # AREA DI LAVORO
    target = st.session_state.get("page", "home")

    if target == "home":
        st.title("Piattaforma Integrata DIMOS")
        col_el, col_gr = st.columns(2)
        with col_el:
            st.subheader("Modulo Elettrolivelle")
            if os.path.exists("montita.jpg"): 
                st.image("montita.jpg", use_container_width=True)
            if st.button("APRI ELETTROLIVELLE"):
                st.session_state["page"] = "livelle"
                st.rerun()
        with col_gr:
            st.subheader("Grafici e Stampe")
            # Uso l'immagine del grafico già caricata
            if os.path.exists("image_6e3d1e.jpg"):
                st.image("image_6e3d1e.jpg", use_container_width=True)
            if st.button("APRI MODULO GRAFICI"):
                st.session_state["page"] = "grafici"
                st.rerun()

    elif target == "livelle":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()

    elif target == "grafici":
        from plotter_mod import run_plotter
        run_plotter()
