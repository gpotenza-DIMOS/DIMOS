import streamlit as st
import os

# 1. Configurazione (Deve essere la prima riga)
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS per eliminare i margini e pulire il layout
st.markdown("""
    <style>
        /* Sidebar scura e logo Microgeo in alto a sx senza spazi */
        [data-testid="stSidebarContent"] {
            background-color: #1a1c23 !important;
            padding-top: 0px !important;
        }
        .microgeo-header {
            margin-top: -50px;
            margin-left: -5px;
        }

        /* Pulsanti Sidebar: Rettangolari e incollati */
        div.stButton > button {
            width: 100% !important;
            background-color: #2d303d !important;
            color: #ffffff !important;
            border: 1px solid #3d4150 !important;
            border-radius: 0px !important;
            text-align: left !important;
            padding: 15px 20px !important;
            margin: 0px !important;
        }
        div.stButton > button:hover {
            border-left: 5px solid #ff4b4b !important;
            background-color: #3d4150 !important;
        }

        /* Rimuove header e padding inutili */
        header { visibility: hidden; }
        .block-container { padding-top: 0rem !important; }
        [data-testid="stSidebarNav"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg")
        with st.container(border=True):
            st.subheader("Login Accesso")
            u = st.text_input("ID", key="login_id")
            p = st.text_input("Password", type="password", key="login_pass")
            if st.button("ACCEDI"):
                if u == "asdf" and p == "asdf":
                    st.session_state["auth"] = True
                    st.rerun()
                else: st.error("Credenziali Errate")
    st.stop()

# --- SIDEBAR: LOGO MICROGEO E MENU ---
with st.sidebar:
    st.markdown('<div class="microgeo-header">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏠 DASHBOARD"): st.session_state["page"] = "home"
    if st.button("📏 ELETTROLIVELLE"): st.session_state["page"] = "el"
    if st.button("📈 GRAFICI & STAMPE"): st.session_state["page"] = "pl"
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"):
        st.session_state["auth"] = False
        st.rerun()

# --- PAGINA PRINCIPALE (HOME) ---
pg = st.session_state.get("page", "home")

if pg == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()

    # --- ZONA IMMAGINI (ESTERNE AI RIQUADRI) ---
    st.markdown("### Modulo Analisi")
    col_img1, col_img2 = st.columns([1, 4])
    with col_img1:
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=120)
    with col_img2:
        if os.path.exists("montita.jpg"):
            st.image("montita.jpg", width=500)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- ZONA COMANDI (RIQUADRI SEPARATI) ---
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            st.markdown("#### Gestione Elettrolivelle")
            st.write("Calcolo mm, Delta C0 e Analisi Statistica Gaussiana.")
            if st.button("AVVIA ELETTROLIVELLE", key="btn_el"):
                st.session_state["page"] = "el"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("#### Grafici e Reportistica")
            st.write("Visualizzazione serie storiche e generazione file Word/Excel.")
            if st.button("AVVIA MODULO GRAFICI", key="btn_pl"):
                st.session_state["page"] = "pl"
                st.rerun()

# --- GESTIONE MODULI ESTERNI ---
elif pg == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()

elif pg == "pl":
    import plotter_mod
    plotter_mod.run_plotter()
