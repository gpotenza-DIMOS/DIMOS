import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from PIL import Image

def run_map_manager():
    st.header("📍 MAPPA & STRUTTURE")

    # 1. Controllo se i dati sono stati caricati nel Plotter
    if 'df_values' not in st.session_state or st.session_state['df_values'] is None:
        st.warning("⚠️ Nessun dato caricato. Torna in 'ANALISI GRAFICA' e carica un file Excel per vedere i sensori sulla mappa.")
        return

    df_values = st.session_state['df_values']
    col_tempo = st.session_state['col_tempo']

    # 2. Layout a colonne: Mappa a sinistra, Dati a destra
    col_mappa, col_info = st.columns([2, 1])

    with col_mappa:
        st.subheader("Inquadramento Strutturale")
        # Visualizzazione dell'immagine di sfondo (es. la foto del cantiere o GIS)
        sfondo = "montita.jpg" # Puoi cambiare questo file con quello della mappa specifica
        if os.path.exists(sfondo):
            image = Image.open(sfondo)
            st.image(image, caption="Vista Struttura / Mappa Sensori", use_container_width=True)
        else:
            st.info("🖼️ Carica un'immagine 'montita.jpg' nella cartella principale per vederla qui come mappa.")

    with col_info:
        st.subheader("Stato Sensori")
        
        # Estrazione ultimi valori disponibili
        last_readings = df_values.iloc[-1]
        last_time = last_readings[col_tempo].strftime('%d/%m/%Y %H:%M')
        
        st.metric("Ultimo Aggiornamento", last_time)
        st.divider()

        # Filtriamo solo le colonne numeriche (escludendo la data) per mostrare i sensori
        cols_sensori = [c for c in df_values.columns if c != col_tempo]
        
        # Selezione rapida per vedere il valore attuale di un sensore
        sensore_sel = st.selectbox("Seleziona un sensore per i dettagli:", cols_sensori)
        
        valore_attuale = last_readings[sensore_sel]
        
        # Determina unità di misura per l'estetica
        unita = "°" if "°" in sensore_sel else "mm" if "mm" in sensore_sel.lower() else "val"
        
        st.markdown(f"""
        <div style="padding:20px; border-radius:10px; background-color:#262730; border-left: 5px solid #ff0000;">
            <h4 style="margin:0;">{sensore_sel}</h4>
            <h2 style="margin:10px 0; color:#ff0000;">{valore_attuale:.3f} {unita}</h2>
            <p style="font-size:0.8em; color:gray;">Valore registrato il {last_time}</p>
        </div>
        """, unsafe_allow_html=True)

    # 3. Mini Grafico di monitoraggio rapido in basso
    st.divider()
    st.subheader(f"Andamento Rapido: {sensore_sel}")
    
    # Mostriamo solo gli ultimi 100 punti per velocità nella mappa
    df_mini = df_values.tail(100)
    
    fig_mini = go.Figure()
    fig_mini.add_trace(go.Scatter(
        x=df_mini[col_tempo], 
        y=df_mini[sensore_sel],
        mode='lines',
        line=dict(color='#ff0000', width=2),
        fill='tozeroy'
    ))
    
    fig_mini.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=30, b=20),
        template="plotly_white",
        xaxis_title="Tempo",
        yaxis_title=unita
    )
    
    st.plotly_chart(fig_mini, use_container_width=True)

    # 4. Tabella riassuntiva di tutti i sensori
    with st.expander("📋 Tabella Riassuntiva Ultimi Valori"):
        riassunto = pd.DataFrame({
            "Sensore": cols_sensori,
            "Ultimo Valore": [f"{df_values[c].iloc[-1]:.4f}" for c in cols_sensori]
        })
        st.dataframe(riassunto, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    run_map_manager()
