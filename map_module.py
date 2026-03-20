import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from geopy.geocoders import Nominatim
import io

def modulo_mappe():
    st.header("🗺️ Modulo Mappe Interattive DIMOS")
    
    tab1, tab2 = st.tabs(["🌍 Mappa Geografica (GIS)", "🖼️ Mappa su Immagine (CAD)"])

    # --- TAB 1: MAPPA GEOGRAFICA ---
    with tab1:
        st.subheader("Visualizzazione Territoriale")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            city_search = st.text_input("Vai a città/indirizzo (es: Ancona)", "")
        with col2:
            coords_input = st.text_input("Oppure inserisci Coordinate (Lat, Lon)", "")
        
        # Logica di posizionamento iniziale
        lat_init, lon_init = 43.6158, 13.5189 # Default Ancona
        
        if city_search:
            geolocator = Nominatim(user_agent="dimos_app")
            location = geolocator.geocode(city_search)
            if location:
                lat_init, lon_init = location.latitude, location.longitude
        elif coords_input:
            try:
                lat_init = float(coords_input.split(",")[0])
                lon_init = float(coords_input.split(",")[1])
            except:
                st.error("Formato coordinate errato. Usa: Lat, Lon")

        # Caricamento Excel per Marker
        st.write("---")
        up_map = st.file_uploader("Carica Excel Sensori (Colonne: Nome, Lat, Lon, Colore)", type=['xlsx'])
        
        m = folium.Map(location=[lat_init, lon_init], zoom_start=13, control_scale=True)
        
        # Strumento per aggiungere/disegnare/spostare manualmente
        draw = Draw(
            export=True,
            filename='marker_dimos.json',
            position='topleft',
            draw_options={'polyline': False, 'rectangle': False, 'circle': False, 'polygon': False, 'circlemarker': False},
            edit_options={'edit': True}
        )
        draw.add_to(m)

        # Se l'utente ha caricato un Excel, piazziamo i marker
        if up_map:
            df_map = pd.read_excel(up_map)
            for _, row in df_map.iterrows():
                folium.Marker(
                    location=[row['Lat'], row['Lon']],
                    popup=row['Nome'],
                    tooltip=row['Nome'],
                    icon=folium.Icon(color=row.get('Colore', 'blue'), icon='info-sign')
                ).add_to(m)

        st_folium(m, width=1000, height=600)

    # --- TAB 2: MAPPA SU IMMAGINE (CAD) ---
    with tab2:
        st.subheader("Posizionamento Sensori su Planimetria/CAD")
        
        img_file = st.file_uploader("Carica Immagine Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        excel_pts = st.file_uploader("Carica Excel punti (Nome, X, Y)", type=['xlsx'], key="ex_cad")

        if img_file:
            from PIL import Image
            img = Image.open(img_file)
            img_width, img_height = img.size

            # Creazione grafico Plotly con immagine di sfondo
            fig = go.Figure()

            # Aggiungi immagine
            fig.add_layout_image(
                dict(
                    source=img,
                    xref="x", yref="y",
                    x=0, y=img_height,
                    sizex=img_width, sizey=img_height,
                    sizing="stretch",
                    opacity=1,
                    layer="below"
                )
            )

            # Configurazione Assi (nascosti)
            fig.update_xaxes(showgrid=False, range=(0, img_width))
            fig.update_yaxes(showgrid=False, range=(0, img_height), scaleanchor="x")

            # Se ci sono dati da Excel, aggiungi i punti
            if excel_pts:
                df_p = pd.read_excel(excel_pts)
                fig.add_trace(go.Scatter(
                    x=df_p['X'], y=df_p['Y'],
                    mode='markers+text',
                    marker=dict(size=12, color='red', symbol='cross'),
                    text=df_p['Nome'],
                    textposition="top center",
                    name="Sensori"
                ))

            # Interattività: l'utente può aggiungere punti cliccando (nello stato della sessione)
            st.write("Puoi zoomare e spostare i sensori usando la barra degli strumenti di Plotly.")
            fig.update_layout(
                width=1000, height=800,
                margin=dict(l=0, r=0, t=0, b=0),
                dragmode='drawpoint' # Permette di disegnare punti
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("💡 Consiglio: Per spostare i sensori in tempo reale su un'immagine in modo 'drag & drop' avanzato, si consiglia di salvare le nuove coordinate X/Y nell'Excel dopo averle identificate sul grafico.")

# Per eseguire questa parte è necessario installare:
# pip install streamlit-folium folium geopy pillow
