import streamlit as st
import os

# 1. Configurazione 
st.set_page_config(page_title="DIMOS", layout="wide", initial_sidebar_state="expanded")

# 2. CSS (Mantenuto identico al tuo originale)
st.markdown("""
    <style>
        [data-testid="stSidebarContent"] { background-color: #1a1c23 !important; padding-top: 0px !important; }
        [data-testid="stSidebarContent"] .stText, [data-testid="stSidebarContent"] label, 
        [data-testid="stSidebarContent"] h1, [data-testid="stSidebarContent"] h2, 
        [data-testid="stSidebarContent"] h3, [data-testid="stSidebarContent"] p { color: #e0e0e0 !important; }
        .stButton > button {
            width: 100%; border-radius: 0px; height: 60px; font-weight: bold;
            text-transform: uppercase; border: 1px solid #444; background-color: #262730; color: white;
        }
        .stButton > button:hover { border-color: #00ff00; color: #00ff00; }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar di Navigazione
with st.sidebar:
    if os.path.exists("logo_microgeo.png"):
        st.image("logo_microgeo.png", width=200)
    
    st.markdown("### NAVIGAZIONE")
    if st.button("🏠 HOME"):
        st.session_state["page"] = "home"
        st.rerun()
    
    if st.button("📊 ANALISI GRAFICA"):
        st.session_state["page"] = "plotter"
        st.rerun()

    if st.button("📍 MAPPA & STRUTTURE"): # NUOVO PULSANTE SIDEBAR
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

    # Logo e Immagine copertina
    col_img1, col_img2 = st.columns([1, 4])
    with col_img1:
        if os.path.exists("logo_DIMOScircle.jpg"): st.image("logo_DIMOScircle.jpg", width=250)
    with col_img2:
        if os.path.exists("montita.jpg"): st.image("montita.jpg", width=400)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # GRIGLIA COMANDI (Aggiunto il terzo modulo)
    c1, c2, c3 = st.columns(3) # Portato a 3 colonne
    
    with c1:
        with st.container(border=True):
            st.markdown("#### Modulo Elettrolivelle")
            st.write("Calcolo cedimenti e analisi statistica.")
            if st.button("Analisi ELETTROLIVELLE", key="btn_el"):
                st.session_state["page"] = "el"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("#### Modulo Grafici")
            st.write("Visualizzazione dati e generazione Report Word.")
            if st.button("Analisi GRAFICA", key="btn_plotter"):
                st.session_state["page"] = "plotter"
                st.rerun()

    with c3: # NUOVO RIQUADRO IN HOME
        with st.container(border=True):
            st.markdown("#### Mappa & Strutture")
            st.write("Posizionamento sensori su GIS o Planimetrie.")
            if st.button("Apri MAPPA", key="btn_map"):
                st.session_state["page"] = "map"
                st.rerun()

# --- LOGICA DI REINDIRIZZAMENTO AI MODULI ---

elif pg == "plotter":
    import plotter_mod
    plotter_mod.run_plotter()

elif pg == "el":
    import elettrolivelle_mod
    elettrolivelle_mod.run_elettrolivelle()

elif pg == "map":
    st.title("📍 Localizzazione Sensori")
    tab1, tab2 = st.tabs(["🌍 Monitoraggio Territoriale (GIS)", "🏗️ Monitoraggio Strutturale (Foto)"])
    
    with tab1:
        st.info("In questa sezione potrai visualizzare i sensori su mappa satellitare.")
        # Qui richiameremo: map_module.render_territorial()
        
    with tab2:
        st.info("In questa sezione potrai caricare una foto della struttura e posizionare i sensori.")
        uploaded_map = st.file_uploader("Carica Planimetria o Foto Struttura", type=["jpg", "png", "jpeg"])
        if uploaded_map:
            st.image(uploaded_map, caption="Layout della struttura")
            st.warning("Funzionalità di posizionamento punti in fase di configurazione.")
