import streamlit as st
import os

# 1. Configurazione Pagina (Deve essere la prima istruzione)
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS Avanzato per ricalcare screen1.jpg
st.markdown("""
    <style>
        /* Sfondo Sidebar Scuro Totale */
        [data-testid="stSidebar"] {
            background-color: #1a1c23 !important;
            min-width: 300px !important;
        }
        
        /* Posizionamento Logo Circolare in alto a sinistra senza margini */
        .logo-top {
            margin-top: -50px;
            margin-left: -10px;
            margin-bottom: 20px;
        }

        /* Container per i pulsanti per tenerli vicini */
        .button-container {
            margin-top: 10px;
        }

        /* STILE PULSANTI (Grigio scuro, testo allineato a sinistra, animati) */
        div.stButton > button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #d1d1d1 !important;
            border: 1px solid #3d4150 !important;
            padding: 10px 15px !important;
            text-align: left !important;
            font-weight: 500 !important;
            border-radius: 4px !important;
            transition: all 0.2s ease !important;
            display: block !important;
            margin-bottom: -10px !important; /* Avvicina i pulsanti tra loro */
        }

        /* Hover: Effetto sollevamento e bordo rosso sottile */
        div.stButton > button:hover {
            background-color: #3d4150 !important;
            color: #ffffff !important;
            border-color: #ff4b4b !important;
            transform: translateX(5px) !important; /* Slitta leggermente a destra */
        }

        /* Active: Effetto click */
        div.stButton > button:active {
            transform: scale(0.98) !important;
            background-color: #1a1c23 !important;
        }

        /* Posizionamento Logo Microgeo in fondo alla Sidebar */
        .sidebar-footer {
            position: fixed;
            bottom: 20px;
            left: 20px;
            width: 260px;
        }

        /* Nascondi elementi Streamlit che sporcano il design */
        header {visibility: hidden;}
        [data-testid="stSidebarNav"] {display: none;}
        .block-container {padding-top: 1rem;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONE LOGIN (Invariata) ---
def login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if os.path.exists("logo_dimos.jpg"):
                st.image("logo_dimos.jpg", use_container_width=True)
            with st.container(border=True):
                st.subheader("Login Accesso")
                uid = st.text_input("ID")
                psw = st.text_input("Password", type="password")
                if st.button("ACCEDI"):
                    if uid == "asdf" and psw == "asdf":
                        st.session_state["authenticated"] = True
                        st.rerun()
                    else: st.error("Credenziali non corrette")
        return False
    return True

# --- LOGICA APP ---
if login():
    # SIDEBAR PERSONALIZZATA
    with st.sidebar:
        # Logo in alto a sinistra
        st.markdown('<div class="logo-top">', unsafe_allow_html=True)
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=110)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Pulsanti MENU
        st.markdown('<div class="button-container">', unsafe_allow_html=True)
        if st.button("🏠 DASHBOARD"): st.session_state["menu"] = "home"
        if st.button("📏 ELETTROLIVELLE"): st.session_state["menu"] = "livelle"
        if st.button("📈 GRAFICI & STAMPE"): st.session_state["menu"] = "grafici"
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Footer con Logo Microgeo e Logout
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        if os.path.exists("logo_microgeo.jpg"):
            st.image("logo_microgeo.jpg", width=180)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 ESCI"):
            st.session_state["authenticated"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # CONTENUTO PRINCIPALE
    pagina = st.session_state.get("menu", "home")
    
    if pagina == "home":
        st.title("Piattaforma Integrata DIMOS")
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Modulo Livellometrico")
            if os.path.exists("montita.jpg"): st.image("montita.jpg", use_container_width=True)
            if st.button("APRI ELETTROLIVELLE"):
                st.session_state["menu"] = "livelle"
                st.rerun()
        with c2:
            st.subheader("Grafici e Stampe")
            if os.path.exists("image_6e2623.jpg"): st.image("image_6e2623.jpg", use_container_width=True)
            if st.button("APRI MODULO GRAFICI"):
                st.session_state["menu"] = "grafici"
                st.rerun()

    elif pagina == "livelle":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()

    elif pagina == "grafici":
        from plotter_mod import run_plotter
        run_plotter()
