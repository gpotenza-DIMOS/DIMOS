import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
from geopy.geocoders import Nominatim
import io

def modulo_mappe_con_link_grafico(anagrafica_sensori):
    st.subheader("🗺️ Mappe e Planimetrie Interattive")
    
    # Inizializziamo lo stato della selezione se non esiste
    if 'sensor_selected_from_map' not in st.session_state:
        st.session_state.sensor_selected_from_map = []

    tab_gis, tab_cad = st.tabs(["🌍 Mappa Geografica", "🖼️ Planimetria CAD"])

    # --- 1. MAPPA GEOGRAFICA (Con correzione errore Foto) ---
    with tab_gis:
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            city = st.text_input("Cerca Località (es. Ancona)", key="city_search")
        
        # FIX ERRORE FOTO: Controllo se location è None
        lat_map, lon_map = 43.6158, 13.5189 # Default
        if city:
            try:
                geolocator = Nominatim(user_agent="dimos_geo")
                location = geolocator.geocode(city)
                if location:
                    lat_map, lon_map = location.latitude, location.longitude
                else:
                    st.warning(f"Località '{city}' non trovata. Uso posizione default.")
            except:
                st.error("Errore di connessione al servizio mappe.")

        st.info("💡 Nota: Per la mappa geografica interattiva con click-to-graph, stiamo usando Plotly per permettere il link diretto ai dati.")
        
        # Simuliamo dei punti geografici dai sensori se hanno coordinate
        # (Qui potresti caricare un excel con Nome, Lat, Lon)
        fig_geo = go.Figure(go.Scattermapbox(
            lat=[lat_map], lon=[lon_map],
            mode='markers+text',
            marker=dict(size=12, color='blue'),
            text=["Centro Operativo"],
            customdata=["NONE"], # ID per il click
        ))
        
        fig_geo.update_layout(
            mapbox=dict(style="open-street-map", center=dict(lat=lat_map, lon=lon_map), zoom=12),
            margin=dict(l=0, r=0, t=0, b=0), height=500
        )
        st.plotly_chart(fig_geo, use_container_width=True)

    # --- 2. PLANIMETRIA CAD (Click-to-Graph) ---
    with tab_cad:
        img_file = st.file_uploader("Carica Immagine CAD", type=['png', 'jpg'])
        coord_file = st.file_uploader("Carica Excel Coordinate (Nome, X, Y)", type=['xlsx'])
        
        if img_file and coord_file:
            img = Image.open(img_file)
            w, h = img.size
            df_coords = pd.read_excel(coord_file)
            
            fig_cad = go.Figure()
            fig_cad.add_layout_image(dict(
                source=img, xref="x", yref="y", x=0, y=h, sizex=w, sizey=h,
                sizing="stretch", layer="below"
            ))
            
            # Aggiungiamo i sensori come punti cliccabili
            fig_cad.add_trace(go.Scatter(
                x=df_coords['X'], y=df_coords['Y'],
                mode='markers+text',
                text=df_coords['Nome'],
                marker=dict(size=15, color='red', symbol='diamond'),
                customdata=df_coords['Nome'], # Questo serve per identificare quale sensore clicchi
                name="Sensori"
            ))
            
            fig_cad.update_xaxes(range=[0, w], showgrid=False)
            fig_cad.update_yaxes(range=[0, h], showgrid=False, scaleanchor="x")
            fig_cad.update_layout(width=1000, height=600, dragmode='drawpoint')

            # CATTURA IL CLICK
            selected_points = st.plotly_chart(fig_cad, use_container_width=True, on_select="rerun")
            
            # Se l'utente clicca su un punto
            if selected_points and "selection" in selected_points:
                points = selected_points["selection"]["points"]
                if points:
                    sensor_clicked = points[0]["customdata"]
                    st.session_state.sensor_selected_from_map = [sensor_clicked]
                    st.success(f"✅ Sensore {sensor_clicked} selezionato! Vai alla sezione Grafici.")

    return st.session_state.sensor_selected_from_map

# --- INTEGRAZIONE NEL MAIN ---
# Quando chiami la parte dei grafici, usa st.session_state.sensor_selected_from_map 
# come valore di default nel multiselect dei sensori.
