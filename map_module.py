import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# 1. Configurazione Iniziale
st.set_page_config(layout="wide", page_title="DIMOS HUB")

# 2. Inizializzazione Session State (Previene i NameError)
if 'sensori_manuali' not in st.session_state:
    st.session_state.sensori_manuali = []

# 3. Sidebar per navigazione e caricamento
st.sidebar.title("📌 Menu Principale")
menu = st.sidebar.radio("Vai a:", ["Mappe", "Grafici"])
file_excel = st.sidebar.file_uploader("Carica Excel (Opzionale)", type=['xlsx', 'xlsm'])

# --- MODULO MAPPE (Indipendente e Manuale) ---
if menu == "Mappe":
    st.header("🗺️ Posizionamento Sensori su Immagine/CAD")
    
    col_input, col_map = st.columns([1, 3])
    
    with col_input:
        st.subheader("➕ Aggiungi Sensore")
        nome = st.text_input("Nome Sensore (es. Pippo)")
        x = st.number_input("Coordinata X", value=0)
        y = st.number_input("Coordinata Y", value=0)
        
        if st.button("Inserisci sulla Mappa"):
            if nome:
                st.session_state.sensori_manuali.append({'Nome': nome, 'X': x, 'Y': y})
                st.rerun()
        
        if st.button("🗑️ Reset Totale"):
            st.session_state.sensori_manuali = []
            st.rerun()
            
        st.divider()
        img_file = st.file_uploader("🖼️ Carica Sfondo (CAD o Foto)", type=['png', 'jpg', 'jpeg'])

    with col_map:
        fig = go.Figure()
        
        # Gestione Sfondo: Immagine o Griglia
        if img_file:
            img = Image.open(img_file)
            w, h = img.size
            fig.add_layout_image(dict(
                source=img, xref="x", yref="y", x=0, y=h, 
                sizex=w, sizey=h, sizing="stretch", layer="below"
            ))
            fig.update_xaxes(range=[0, w], visible=True)
            fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
        else:
            fig.update_xaxes(range=[0, 1000], title="Coordinata X")
            fig.update_yaxes(range=[0, 1000], title="Coordinata Y", scaleanchor="x")
            st.info("Carica un'immagine per usarla come sfondo CAD. Ora vedi una griglia standard.")

        # Disegno dei sensori dalla lista manuale
        if st.session_state.sensori_manuali:
            df_m = pd.DataFrame(st.session_state.sensori_manuali)
            fig.add_trace(go.Scatter(
                x=df_m['X'], y=df_m['Y'],
                mode='markers+text',
                text=df_m['Nome'],
                marker=dict(size=14, color='red', symbol='diamond-dot'),
                textposition="top center"
            ))

        fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- MODULO GRAFICI (Non crasha se manca l'Excel) ---
elif menu == "Grafici":
    st.header("📈 Analisi Dati")
    if file_excel is None:
        st.warning("⚠️ Carica il file Excel nella sidebar per vedere i grafici.")
    else:
        st.success("File caricato correttamente. (Qui andrà la tua logica dei grafici)")
