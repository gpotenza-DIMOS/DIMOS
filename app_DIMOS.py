import streamlit as st
import os

# Configurazione Pagina
st.set_page_config(page_title="DIMOS - Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- CSS AVANZATO PER LOOK "SOFTWARE MODERNO" ---
st.markdown("""
    <style>
        /* Sfondo e Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1a1c23;
            border-right: 1px solid #333;
            min-width: 300px !important;
        }
        
        /* Contenitore Logo in basso alla sidebar */
        .sidebar-footer {
            position: fixed;
            bottom: 20px;
            width: 260px;
            text-align: center;
        }

        /* STILE BOTTONI MODERNI (Effetto Neumorfico/Industrial) */
        div.stButton > button {
            width: 100%;
            background-color: #2d303d;
            color: #d1d1d1;
            border: 1px solid #3d4150;
            padding: 15px 20px;
            text-align: left;
            font-weight: 500;
            border-radius: 8px;
            transition: all 0.2s ease-in-out;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
            margin-bottom: 10px;
        }

        /* Animazione al passaggio del mouse (Hover) */
        div.stButton > button:hover {
            background-color: #3d4150;
            color: #ffffff;
            border-color: #ff4b4b;
            transform: translateY(-2px);
            box-shadow: 4px 4px 10px rgba(0,0,0,0.5);
        }

        /* Effetto pressione (Click) */
        div.stButton > button:active {
            transform: translateY(1px);
            box-shadow: inset 2px 2px 5px rgba(0,0,0,0.5);
            background-color: #1a1c23;
        }

        /* Nascondi header standard Streamlit */
        header {visibility: hidden;}
        .block-container {padding-top: 1rem;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONE LOGGING ---
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
                st.subheader("Login di Sistema")
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

# --- APPLICAZIONE PRINCIPALE ---
if login():
    # SIDEBAR
    with st.sidebar:
        # Logo Circle in Alto
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=120)
        
        st.markdown("<h3 style='color:white; margin-bottom:20px;'>NAVIGAZIONE</h3>", unsafe_allow_html=True)
        
        # Pulsanti con gestione stato
        if st.button("🏠 DASHBOARD"):
            st.session_state["menu"] = "home"
        if st.button("📏 ELETTROLIVELLE"):
            st.session_state["menu"] = "livelle"
        if st.button("📈 GRAFICI & STAMPE"):
            st.session_state["menu"] = "grafici"
        
        # Logo Microgeo fisso in basso
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        if os.path.exists("logo_microgeo.jpg"):
            st.image("logo_microgeo.jpg", width=200)
        if st.button("🚪 LOGOUT"):
            st.session_state["authenticated"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # LOGICA PAGINE
    pagine = st.session_state.get("menu", "home")

    if pagine == "home":
        st.title("Sistema Integrato DIMOS")
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Analisi Livellometrica")
            if os.path.exists("montita.jpg"):
                st.image("montita.jpg", use_container_width=True)
            if st.button("LANCIA MODULO LIVELLOMETRICO"):
                st.session_state["menu"] = "livelle"
                st.rerun()

        with c2:
            st.markdown("### Monitoraggio & Report")
            # Uso l'immagine del grafico caricata (image_6e2623.jpg)
            if os.path.exists("image_6e2623.jpg"):
                st.image("image_6e2623.jpg", use_container_width=True)
            if st.button("LANCIA MODULO GRAFICI"):
                st.session_state["menu"] = "grafici"
                st.rerun()

    elif pagine == "livelle":
        from elettrolivelle_mod import run_elettrolivelle
        run_elettrolivelle()

    elif pagine == "grafici":
        from plotter_mod import run_plotter
        run_plotter()
