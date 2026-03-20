import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
from geopy.geocoders import Nominatim

def modulo_mappe_con_link_grafico(anagrafica):
    st.subheader("🗺️ Mappe e Planimetrie Interattive")
    
    # 1. Inizializzazione Session State per il "Link" ai grafici
    if 'selected_sensor' not in st.session_state:
        st.session_state.selected_sensor = None

    tab_gis, tab_cad = st.tabs(["🌍 Mappa Geografica", "🖼️ Planimetria CAD"])

    # --- TAB GEOGRAFICA ---
    with tab_gis:
        c1, c2 = st.columns([2, 1])
        with c1:
            city = st.text_input("Cerca Località (es. Ancona)", key="geo_search")
        
        lat, lon = 43.6158, 13.5189 # Default
        if city:
            try:
                geolocator = Nominatim(user_agent="dimos_app_v2")
                loc = geolocator.geocode(city)
                if loc:
                    lat, lon = loc.latitude, loc.longitude
                else:
                    st.warning("Località non trovata.")
            except:
                st.error("Servizio mappe non disponibile.")

        # Visualizzazione Mappa con Plotly (permette il click)
        fig_geo = go.Figure(go.Scattermapbox(
            lat=[lat], lon=[lon],
            mode='markers+text',
            marker=dict(size=12, color='blue'),
            text=["Punto Ricerca"],
            hoverinfo='text'
        ))
        
        fig_geo.update_layout(
            mapbox=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=12),
            margin=dict(l=0, r=0, t=0, b=0), height=500
        )
        st.plotly_chart(fig_geo, use_container_width=True)

    # --- TAB PLANIMETRIA (La tua foto CAD) ---
    with tab_cad:
        st.info("Carica la planimetria e l'Excel con le coordinate X,Y per posizionare i sensori.")
        up_img = st.file_uploader("1. Carica Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'], key="cad_img")
        up_coord = st.file_uploader("2. Carica Excel Coordinate (Colonne: Nome, X, Y)", type=['xlsx'], key="cad_ex")

        if up_img and up_coord:
            img = Image.open(up_img)
            w, h = img.size
            df_coords = pd.read_excel(up_coord)
            
            fig_cad = go.Figure()
            # Sfondo CAD
            fig_cad.add_layout_image(dict(
                source=img, xref="x", yref="y", x=0, y=h, sizex=w, sizey=h,
                sizing="stretch", layer="below"
            ))
            
            # Marker Sensori
            fig_cad.add_trace(go.Scatter(
                x=df_coords['X'], y=df_coords['Y'],
                mode='markers+text',
                text=df_coords['Nome'],
                textfont=dict(color="yellow"),
                marker=dict(size=18, color='red', symbol='diamond-dot'),
                customdata=df_coords['Nome'], # ID fondamentale per il click
                name="Sensori"
            ))
            
            fig_cad.update_xaxes(range=[0, w], showgrid=False, visible=False)
            fig_cad.update_yaxes(range=[0, h], showgrid=False, visible=False, scaleanchor="x")
            fig_cad.update_layout(width=1000, height=700, margin=dict(l=0, r=0, t=0, b=0))

            # GESTIONE DEL CLICK
            # Usiamo on_select per catturare il sensore cliccato
            sel_event = st.plotly_chart(fig_cad, use_container_width=True, on_select="rerun")
            
            if sel_event and "selection" in sel_event and sel_event["selection"]["points"]:
                nome_cliccato = sel_event["selection"]["points"][0]["customdata"]
                st.session_state.selected_sensor = nome_cliccato
                st.success(f"🎯 Sensore **{nome_cliccato}** selezionato! Vai alla scheda Grafici.")

# --- COME CHIAMARLO NEL CODICE PRINCIPALE ---
# Nel punto in cui gestisci i menu (es. if scelta == "Mappe"):
# modulo_mappe_con_link_grafico(anagrafica)
