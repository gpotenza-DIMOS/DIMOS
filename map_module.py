import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# 1. SETUP PAGINA
st.set_page_config(layout="wide", page_title="DIMOS HUB")

# 2. INIZIALIZZAZIONE VARIABILI (Così non avrai MAI più NameError)
if 'sensori_manuali' not in st.session_state:
    st.session_state.sensori_manuali = []

# 3. INTERFACCIA SIDEBAR
st.sidebar.title("MENU DIMOS")
scelta = st.sidebar.selectbox("Vai a:", ["Mappe", "Grafici"])
file_excel = st.sidebar.file_uploader("Carica Excel (Opzionale)", type=['xlsx', 'xlsm'])

# --- MODULO MAPPE (INDIPENDENTE) ---
if scelta == "Mappe":
    st.header("🗺️ Posizionamento Sensori (Manuale o CAD)")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("➕ Aggiungi Punto")
        nuovo_nome = st.text_input("Nome (es. Pippo)")
        coord_x = st.number_input("X", value=0)
        coord_y = st.number_input("Y", value=0)
        
        if st.button("Posiziona Sensore"):
            if nuovo_nome:
                st.session_state.sensori_manuali.append({'Nome': nuovo_nome, 'X': coord_x, 'Y': coord_y})
                st.success(f"'{nuovo_nome}' inserito!")
        
        if st.button("Reset Mappa"):
            st.session_state.sensori_manuali = []
            st.rerun()
            
        st.divider()
        img_sfondo = st.file_uploader("Carica Planimetria/CAD", type=['png', 'jpg', 'jpeg'])

    with col2:
        fig = go.Figure()
        
        # Se carichi un'immagine (tipo il tuo CAD), diventa lo sfondo
        if img_sfondo:
            immagine = Image.open(img_sfondo)
            w, h = immagine.size
            fig.add_layout_image(dict(
                source=immagine, xref="x", yref="y", x=0, y=h, 
                sizex=w, sizey=h, sizing="stretch", layer="below"
            ))
            fig.update_xaxes(range=[0, w], visible=True)
            fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
        else:
            # Griglia libera se non c'è immagine
            fig.update_xaxes(range=[0, 1000], title="X")
            fig.update_yaxes(range=[0, 1000], title="Y", scaleanchor="x")
            st.info("Nessuna immagine: usa la griglia 1000x1000 per posizionare Pippo.")

        # Disegna i sensori inseriti manualmente
        if st.session_state.sensori_manuali:
            df_m = pd.DataFrame(st.session_state.sensori_manuali)
            fig.add_trace(go.Scatter(
                x=df_m['X'], y=df_m['Y'],
                mode='markers+text',
                text=df_m['Nome'],
                marker=dict(size=15, color='red', symbol='x'),
                textposition="top center"
            ))

        fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- MODULO GRAFICI (NON CRASHA SE MANCA FILE) ---
elif scelta == "Grafici":
    st.header("📈 Analisi Dati")
    if file_excel is None:
        st.warning("Per vedere i grafici devi caricare il file Excel dalla sidebar.")
    else:
        st.success("File caricato. Qui andrà la logica dei grafici.")
