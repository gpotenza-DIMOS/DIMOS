import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import io
from PIL import Image

# Configurazione tipi di sensore e colori associati
SENSOR_TYPES = {
    "Elettrolivella": "#FF0000",   # Rosso
    "Fessurimetro": "#00FF00",    # Verde
    "Inclinometro": "#0000FF",    # Blu
    "Estensimetro": "#FFFF00",    # Giallo
    "Piezometro": "#FF00FF"       # Magenta
}

def render_territorial():
    st.subheader("🌍 Posizionamento Territoriale (OpenStreetMap)")
    
    if 'geo_sensors' not in st.session_state:
        st.session_state['geo_sensors'] = []

    # Coordinate iniziali (es. Sede Microgeo o centro Italia)
    initial_lat, initial_lon = 43.8248, 11.1222 

    st.info("Clicca sulla mappa per ottenere le coordinate, seleziona il tipo e conferma il posizionamento.")

    # Creazione mappa base
    fig = px.scatter_mapbox(
        lat=[initial_lat], lon=[initial_lon],
        zoom=12, height=600
    )
    
    # Se ci sono sensori salvati, li aggiungiamo
    if st.session_state['geo_sensors']:
        df = pd.DataFrame(st.session_state['geo_sensors'])
        for s_type, group in df.groupby("type"):
            fig.add_trace(go.Scattermapbox(
                lat=group["lat"], lon=group["lon"],
                mode='markers+text',
                marker=go.scattermapbox.Marker(size=14, color=SENSOR_TYPES.get(s_type, "#FFFFFF")),
                text=group["name"],
                name=s_type,
                hoverinfo="text"
            ))

    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r":0,"t":0,"l":0,"b":0},
        clickmode='event+select'
    )

    # Visualizzazione mappa e cattura click
    selected_point = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # Pannello di controllo posizionamento
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        s_name = c1.text_input("ID Sensore", placeholder="es. Liv-01", key="geo_name")
        s_type = c2.selectbox("Tipologia", list(SENSOR_TYPES.keys()), key="geo_type")
        
        # Gestione coordinate da click (se supportato dal browser/plotly)
        st.caption("Nota: Inserisci le coordinate lette dal cursore sulla mappa per precisione.")
        lat_in = c3.number_input("Lat", format="%.6f", value=initial_lat)
        lon_in = c3.number_input("Lon", format="%.6f", value=initial_lon)

        if c4.button("📍 PIAZZA", use_container_width=True):
            st.session_state['geo_sensors'].append({"name": s_name, "lat": lat_in, "lon": lon_in, "type": s_type})
            st.rerun()

def render_structural():
    st.subheader("🏗️ Layout su Foto Struttura")
    
    img_file = st.file_uploader("Carica foto struttura", type=["jpg", "png", "jpeg"])
    
    if img_file:
        if 'struc_sensors' not in st.session_state:
            st.session_state['struc_sensors'] = []

        image = Image.open(img_file)
        width, height = image.size

        fig = go.Figure()
        fig.add_layout_image(
            dict(source=image, xref="x", yref="y", x=0, y=height, sizex=width, sizey=height, 
                 sizing="stretch", layer="below")
        )
        
        # Disegno sensori esistenti
        if st.session_state['struc_sensors']:
            df = pd.DataFrame(st.session_state['struc_sensors'])
            for s_type, group in df.groupby("type"):
                fig.add_trace(go.Scatter(
                    x=group["x"], y=group["y"], mode='markers+text',
                    marker=dict(color=SENSOR_TYPES.get(s_type, "#FFF"), size=15, symbol='square'),
                    text=group["name"], textposition="top center", name=s_type
                ))

        fig.update_xaxes(range=[0, width], visible=False)
        fig.update_yaxes(range=[0, height], visible=False, scaleanchor="x")
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=600, showlegend=True)

        st.plotly_chart(fig, use_container_width=True)

        # Pannello manuale
        with st.container(border=True):
            st.write("Identifica le coordinate passando il mouse sulla foto:")
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
            n = c1.text_input("Nome", key="st_name")
            t = c2.selectbox("Tipo", list(SENSOR_TYPES.keys()), key="st_type")
            x = c3.number_input("X", value=0)
            y = c4.number_input("Y", value=0)
            if c5.button("✅ AGGIUNGI", use_container_width=True):
                st.session_state['struc_sensors'].append({"name": n, "x": x, "y": y, "type": t})
                st.rerun()

def run_map_manager():
    t1, t2 = st.tabs(["🌍 MAPPA TERRITORIALE", "🖼️ LAYOUT FOTO"])
    with t1: render_territorial()
    with t2: render_structural()
