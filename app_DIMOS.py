import streamlit as st
import os

# 1. Configurazione 
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS margini e layout (ORIGINALE INTEGRALE)
st.markdown("""
    <style>
        /* Sidebar scura e logo Microgeo in alto a sx senza spazi */
        [data-testid="stSidebarContent"] {
            background-color: #1a1c23 !important;
            padding-top: 0px !important;
        }
        
        /* MODIFICA COLORI TESTO SIDEBAR: Grigio chiaro per leggibilità */
        [data-testid="stSidebarContent"] .stText, 
        [data-testid="stSidebarContent"] label, 
        [data-testid="stSidebarContent"] h1, 
        [data-testid="stSidebarContent"] h2, 
        [data-testid="stSidebarContent"] h3, 
        [data-testid="stSidebarContent"] p {
            color: #e0e0e0 !important;
        }
        /* Colore specifico per i numeri/testo dentro i widget della sidebar */
        [data-testid="stSidebarContent"] .stMarkdown {
            color: #b8b8b8 !important;
        }

        .microgeo-header {
            margin-top: -50px;
            margin-left: -5px;
        }

        /* Pulsanti Sidebar: Rettangolari e Scritta Bianca */
        .stButton > button {
            width: 100%;
            border-radius: 0px;
            height: 60px;
            font-weight: bold;
            text-transform: uppercase;
            border: 1px solid #444;
            background-color: #262730;
            color: white;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            border-color: #00ff00;
            color: #00ff00;
            background-color: #333;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar di Navigazione
with st.sidebar:
    # --- LOGO GRANDE POSIZIONATO IN ALTO (ORIGINALE) ---
    st.markdown('<div class="microgeo-header">', unsafe_allow_html=True)
    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", use_container_width=True)
    elif os.path.exists("logo_microgeo.png"):
        st.image("logo_microgeo.png", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### NAVIGAZIONE")
    if st.button("🏠 HOME"):
        st.session_state["page"] = "home"
        st.rerun()
    
    if st.button("📊 ANALISI GRAFICA"):
        st.session_state["page"] = "plotter"
        st.rerun()

    if st.button("📍 MAPPA & STRUTTURE"):
        st.session_state["page"] = "map"
        st.rerun()
        
    if st.button("📈 ELETTROLIVELLE"):
        st.session_state["page"] = "el"
        st.rerun()

# 4. Gestione Pagine
pg = st.session_state.get("page", "home")

if pg == "home":
    st.title("Piattaforma Integrata DIMOS")
    st.divider()

    # --- ZONA IMMAGINI (ESTERNE AI RIQUADRI) ---
    st.markdown("### Gestione e Analisi")
    col_img1, col_img2 = st.columns([1, 4])
    with col_img1:
        if os.path.exists("logo_DIMOScircle.jpg"):
            st.image("logo_DIMOScircle.jpg", width=250)
    with col_img2:
        if os.path.exists("montita.jpg"):
            st.image("montita.jpg", width=400)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- ZONA COMANDI (TRE COLONNE) ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        with st.container(border=True):
            st.markdown("#### Modulo Elettrolivelle")
            st.write("Calcolo cedimenti, Grafici e Analisi Statistica.")
            if st.button("Analisi ELETTROLIVELLE", key="btn_el"):
                st.session_state["page"] = "el"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("#### Modulo Grafici")
            st.write("Visualizzazione Dati e Reportistica Word.")
            if st.button("Analisi GRAFICA", key="btn_plotter"):
                st.session_state["page"] = "plotter"
                st.rerun()

    with c3:
        with st.container(border=True):
            st.markdown("#### Mappa & Strutture")
            st.write("Posizionamento sensori su GIS o Foto.")
            if st.button("Apri MAPPA", key="btn_map"):
                st.session_state["page"] = "map"
                st.rerun()

    # --- FOOTER ---
    st.divider()
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        st.markdown("""
            ### Contatti e Supporto
            **Microgeo S.r.l.** 📍 Via de' Barucci 4, 50127 Firenze (FI)  
            📞 +39 055 4220471  
            📧 [info@microgeo.it](mailto:info@microgeo.it)  
            🌐 [www.microgeo.it](https://www.microgeo.it)
        """)
    with col_f2:
        st.markdown("### Seguici")
        st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/microgeo-srl/)")
        st.markdown("[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/user/MicrogeoSrl)")

    if os.path.exists("logo_microgeo.jpg"):
        st.image("logo_microgeo.jpg", width=150)
    elif os.path.exists("logo_microgeo.png"):
        st.image("logo_microgeo.png", width=150)

# --- LOGICA REINDIRIZZAMENTO ---
elif pg == "plotter":
    import plotter_mod
    plotter_mod.run_plotter()

elif pg == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()

elif pg == "map":
    st.title("📍 Localizzazione Sensori")
    t1, t2 = st.tabs(["Mappa GIS", "Layout Strutturale"])
    with t1:
        st.info("Visualizzazione territoriale.")
    with t2:
        st.info("Posizionamento sensori su immagine struttura.")
        up = st.file_uploader("Carica immagine", type=["jpg","png"])
        if up: st.image(up)
