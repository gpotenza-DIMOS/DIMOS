import streamlit as st
import os

# Configurazione Pagina
st.set_page_config(page_title="DIMOS - Monitoring System", layout="wide", initial_sidebar_state="expanded")

# --- CSS AVANZATO PER POSIZIONAMENTO E ANIMAZIONI ---
st.markdown("""
    <style>
        /* Sfondo Sidebar scuro e pulito */
        [data-testid="stSidebar"] {
            background-color: #1a1c23;
            border-right: 1px solid #333;
        }
        
        /* Contenitore Logo Microgeo fisso in fondo alla sidebar */
        .sidebar-footer {
            position: fixed;
            bottom: 30px;
            width: 260px;
            text-align: center;
        }

        /* STILE PULSANTI MODERNI CON ANIMAZIONE */
        div.stButton > button {
            width: 100%;
            background-color: #2d303d;
            color: #d1d1d1;
            border: 1px solid #3d4150;
            padding: 12px 15px;
            text-align: left;
            font-weight: 500;
            border-radius: 6px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.85rem;
        }

        /* Hover: si illumina e si alza */
        div.stButton > button:hover {
            background-color: #3d4150;
            color: #ffffff;
            border-color: #ff4b4b;
            transform: translateY(-3px);
            box-shadow: 5px 5px 15px rgba(0,0,0,0.4);
        }

        /* Active: effetto pressione fisica */
        div.stButton > button:active {
            transform: translateY(1px);
            box-shadow: inset 2px 2px 8px rgba(0,0,0,0.5);
            background-color: #1a1c23;
        }

        /* Rimuove elementi inutili di Streamlit */
        header {visibility: hidden;}
        .block-container {padding-top: 1rem;}
        
        /* Titoli sezioni sidebar */
        .sidebar-header {
            color: #555;
            font-size: 0.7rem;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
            padding-left: 5px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN (Invariato come richiesto) ---
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
                    else:
                        st.error("Credenziali non corrette")
        return False
    return True

# --- APP PRINCIPALE ---
if login():
    # BARRA LATERALE (LAYOUT COME DA SCREENSHOT)
    with st.sidebar:
        # 1. Logo Circolare in alto
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=120)
        
        st.markdown('<p class="sidebar-header">MENU PRINCIPALE</p>', unsafe_allow_html=True)
        
        # 2. Pulsanti Navigazione
        if st.button("🏠 DASHBOARD"):
            st.session_state["menu"] = "home"
        if st.button("📏 ELETTROLIVELLE"):
            st.session_state["menu"] = "livelle"
        if st.button("📈 GRAFICI & STAMPE"):
            st.session_state["menu"] = "grafici"
        
        # 3. Logo Microgeo fisso in fondo
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        if os.path.exists("logo_microgeo.jpg"):
            st.image("logo_microgeo.jpg", width=180)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 ESCI"):
            st.session_state["authenticated"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- LOGICA PAGINE ---
    pagine = st.session_state.get("menu", "home")

    if pagine == "home":
        st.title("Piattaforma Integrata DIMOS")
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Analisi Livellometrica")
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            if st.button("AVVIA MODULO LIVELLOMETRICO"):
                st.session_state["menu"] = "livelle"
                st.rerun()

        with c2:
            st.markdown("### Monitoraggio & Report")
            if os.path.exists("image_6e2623.jpg"):
                st.image("image_6e2623.jpg", use_container_width=True)
            if st.button("AVVIA MODULO GRAFICI"):
                st.session_state["menu"] = "grafici"
                st.rerun()

    elif pagine == "livelle":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()

    elif pagine == "grafici":
        from plotter_mod import run_plotter
        run_plotter()
