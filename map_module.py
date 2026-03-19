import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import os
import json

# --- GESTIONE DATABASE POSIZIONI ---
# Questo file salva dove hai messo i sensori così non devi rifarlo ogni volta
CONFIG_FILE = "sensor_positions.json"

def load_positions():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_positions(positions):
    with open(CONFIG_FILE, "w") as f:
        json.dump(positions, f)

def run_map_manager():
    st.header("📍 Centro Controllo Mappe")

    # Verifica se ci sono dati caricati dal plotter
    if 'df_values' not in st.session_state:
        st.warning("⚠️ Carica prima un file Excel nel modulo 'ANALISI GRAFICA' per importare i nomi dei sensori.")
        return

    df = st.session_state['df_values']
    col_t = st.session_state['col_tempo']
    sensori_disponibili = [c for c in df.columns if c != col_t]
    
    # Carica posizioni salvate
    posizioni_salvate = load_positions()

    tab_img, tab_gis = st.tabs(["🏗️ Mappa Strutturale (Immagine)", "🌍 Mappa Territoriale (GIS)"])

    # --- SCHEDA 1: MAPPA SU IMMAGINE ---
    with tab_img:
        st.subheader("Posizionamento Sensori su Foto/Disegno")
        
        up_img = st.file_uploader("Carica Planimetria o Foto (JPG/PNG)", type=["jpg", "png", "jpeg"])
        img_path = "map_background.jpg"
        
        if up_img:
            img = Image.open(up_img)
            img.save(img_path)
        
        if os.path.exists(img_path):
            img = Image.open(img_path)
            width, height = img.size
            
            st.info("💡 Seleziona un sensore e clicca sulla mappa per posizionarlo.")
            
            col_sel, col_reset = st.columns([3, 1])
            with col_sel:
                sensore_da_piazzare = st.selectbox("1. Scegli Sensore da Excel:", sensori_disponibili)
            
            # Creazione del grafico Plotly con l'immagine come sfondo
            fig = go.Figure()

            # Aggiunta immagine di sfondo
            fig.add_layout_image(
                dict(source=img, x=0, y=height, sizex=width, sizey=height, 
                     xref="x", yref="y", sizing="stretch", opacity=1, layer="below")
            )

            # Preparazione dati per i sensori già posizionati
            x_pos, y_pos, names, values = [], [], [], []
            for s in sensori_disponibili:
                if s in posizioni_salvate.get("image", {}):
                    p = posizioni_salvate["image"][s]
                    x_pos.append(p['x'])
                    y_pos.append(p['y'])
                    names.append(s)
                    values.append(df[s].iloc[-1]) # Ultimo valore letto

            # Disegno dei sensori sulla mappa
            fig.add_trace(go.Scatter(
                x=x_pos, y=y_pos, mode='markers+text',
                marker=dict(size=15, color='red', symbol='circle'),
                text=[f"{n}<br>{v:.2f}" for n, v in zip(names, values)],
                textposition="top center",
                hovertemplate="<b>%{text}</b><extra></extra>",
                name="Sensori Posizionati"
            ))

            fig.update_xaxes(range=[0, width], showgrid=False, zeroline=False, visible=False)
            fig.update_yaxes(range=[0, height], showgrid=False, zeroline=False, visible=False)
            fig.update_layout(width=width, height=height, margin=dict(l=0, r=0, t=0, b=0), clickmode='event+select')

            # Cattura del click per posizionare (Simulazione Drag&Drop)
            selected_point = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            
            # Se l'utente clicca, salviamo la nuova posizione
            if selected_point and "points" in selected_point and selected_point["points"]:
                pt = selected_point["points"][0]
                new_x, new_y = pt['x'], pt['y']
                
                if "image" not in posizioni_salvate: posizioni_salvate["image"] = {}
                posizioni_salvate["image"][sensore_da_piazzare] = {"x": new_x, "y": new_y}
                save_positions(posizioni_salvate)
                st.success(f"Sensore {sensore_da_piazzare} posizionato!")
                st.rerun()

    # --- SCHEDA 2: MAPPA TERRITORIALE (GIS) ---
    with tab_gis:
        st.subheader("Monitoraggio Ambientale su Mappa OpenStreetMap")
        
        # Centro mappa (default Campi Bisenzio o media sensori)
        m_lat, m_lon = 43.82, 11.13 
        
        fig_gis = px.scatter_mapbox(
            lat=[], lon=[], text=[], size_max=15, zoom=10
        )
        
        # Qui potremmo integrare Folium per un Drag&Drop GIS reale
        st.warning("In questa sezione puoi inserire le coordinate Lat/Lon nell'Excel per vedere i sensori sul territorio.")
        
        # Esempio tabella per inserimento manuale coordinate
        with st.expander("Modifica Coordinate Geografiche"):
            # Logica per inserire Lat/Lon se non presenti nell'Excel
            st.write("Funzione in fase di sviluppo per il mapping GIS...")
