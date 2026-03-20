import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# 1. SETTAGGI TABELLA DI MARCIA
st.set_page_config(layout="wide", page_title="DIMOS HUB")

# 2. INIZIALIZZAZIONE VARIABILI DI SESSIONE (Previene ogni errore di "Name Not Defined")
if 'sensori_manuali' not in st.session_state:
    st.session_state.sensori_manuali = []
if 'anagrafica_dati' not in st.session_state:
    st.session_state.anagrafica_dati = None

# 3. SIDEBAR - CARICAMENTO OPZIONALE
st.sidebar.title("⚙️ Pannello Controllo")
menu = st.sidebar.radio("Scegli Modulo:", ["Mappe", "Grafici"])
file_uade = st.sidebar.file_uploader("📂 Carica Excel Monitoraggio (Opzionale)", type=['xlsx', 'xlsm'])

# Logica di caricamento anagrafica solo se il file esiste
if file_uade:
    try:
        xls = pd.ExcelFile(file_uade)
        if "NAME" in xls.sheet_names:
            df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
            ana = {}
            for c in range(1, df_n.shape[1]):
                dl = str(df_n.iloc[0, c]).strip()
                sn = str(df_n.iloc[1, c]).strip()
                if dl:
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sn] = {}
            st.session_state.anagrafica_dati = ana
    except:
        st.sidebar.error("Errore lettura file, ma puoi usare le Mappe manualmente.")

# --- MODULO MAPPE (LIBERTA' ASSOLUTA) ---
if menu == "Mappe":
    st.header("🗺️ Layout Sensori e Planimetrie")
    
    col_sx, col_dx = st.columns([1, 3])
    
    with col_sx:
        st.subheader("📍 Nuovo Marker")
        nome_m = st.text_input("Nome Sensore (es. Pippo)")
        pos_x = st.number_input("Coordinata X", value=0)
        pos_y = st.number_input("Coordinata Y", value=0)
        
        if st.button("Aggiungi alla Mappa"):
            if nome_m:
                st.session_state.sensori_manuali.append({'Nome': nome_m, 'X': pos_x, 'Y': pos_y})
                st.rerun()
        
        if st.button("🗑️ Svuota Tutto"):
            st.session_state.sensori_manuali = []
            st.rerun()
            
        st.divider()
        planimetria = st.file_uploader("🖼️ Carica Sfondo (CAD/Immagine)", type=['png', 'jpg', 'jpeg'])

    with col_dx:
        fig = go.Figure()
        
        if planimetria:
            img_cad = Image.open(planimetria)
            w, h = img_cad.size
            fig.add_layout_image(dict(
                source=img_cad, xref="x", yref="y", x=0, y=h, 
                sizex=w, sizey=h, sizing="stretch", layer="below"
            ))
            fig.update_xaxes(range=[0, w], visible=True)
            fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
        else:
            fig.update_xaxes(range=[0, 1000], title="Asse X")
            fig.update_yaxes(range=[0, 1000], title="Asse Y", scaleanchor="x")
            st.info("Griglia neutra attiva. Carica un'immagine per lo sfondo.")

        if st.session_state.sensori_manuali:
            df_m = pd.DataFrame(st.session_state.sensori_manuali)
            fig.add_trace(go.Scatter(
                x=df_m['X'], y=df_m['Y'],
                mode='markers+text',
                text=df_m['Nome'],
                marker=dict(size=15, color='red', symbol='x-dot'),
                textposition="top center"
            ))

        fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- MODULO GRAFICI (NON CRASHA MAI) ---
elif menu == "Grafici":
    st.header("📈 Analisi Dati")
    if st.session_state.anagrafica_dati is None:
        st.warning("⚠️ Carica un file Excel valido nella sidebar per abilitare questo modulo.")
    else:
        st.success("Dati pronti. Seleziona i sensori dall'elenco.")
        # Qui puoi rimettere la tua logica dei grafici sapendo che 'st.session_state.anagrafica_dati' esiste
