import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# 1. Inizializzazione Session State - Questo impedisce i crash "NameError"
if 'sensori_manuali' not in st.session_state:
    st.session_state.sensori_manuali = []

st.set_page_config(layout="wide", page_title="DIMOS HUB")

# 2. Sidebar pulita
st.sidebar.title("📌 Navigazione")
menu = st.sidebar.radio("Vai a:", ["Mappe", "Grafici"])

# Il caricamento file non deve bloccare nulla
file_input = st.sidebar.file_uploader("Carica Excel (Opzionale)", type=['xlsx', 'xlsm'])

# --- MODULO MAPPE (Indipendente) ---
if menu == "Mappe":
    st.header("🗺️ Mappe e Planimetrie")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("➕ Inserimento Manuale")
        nome_s = st.text_input("Nome Sensore", value="Pippo")
        x_s = st.number_input("Coordinata X", value=0)
        y_s = st.number_input("Coordinata Y", value=0)
        
        if st.button("Posiziona"):
            if nome_s:
                st.session_state.sensori_manuali.append({'Nome': nome_s, 'X': x_s, 'Y': y_s})
                st.rerun()
        
        if st.button("🗑️ Svuota Mappa"):
            st.session_state.sensori_manuali = []
            st.rerun()
            
        st.divider()
        img_file = st.file_uploader("🖼️ Carica Sfondo (CAD/JPG)", type=['png', 'jpg', 'jpeg'])

    with col2:
        fig = go.Figure()
        
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
            # Griglia di default se non carichi nulla
            fig.update_xaxes(range=[0, 1000], title="X")
            fig.update_yaxes(range=[0, 1000], title="Y", scaleanchor="x")
            st.info("Visualizzazione su griglia standard. Carica un'immagine per lo sfondo.")

        # Disegna i sensori inseriti
        if st.session_state.sensori_manuali:
            df_points = pd.DataFrame(st.session_state.sensori_manuali)
            fig.add_trace(go.Scatter(
                x=df_points['X'], y=df_points['Y'],
                mode='markers+text',
                text=df_points['Nome'],
                marker=dict(size=15, color='red', symbol='diamond'),
                textposition="top center"
            ))

        fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- MODULO GRAFICI (Protettivo) ---
elif menu == "Grafici":
    st.header("📈 Grafici")
    # Qui controlliamo se esiste la variabile anagrafica PRIMA di usarla
    if 'anagrafica' not in locals() and 'anagrafica' not in globals():
        st.warning("⚠️ Carica il file Excel per abilitare i grafici.")
    else:
        st.write("Dati pronti.")
