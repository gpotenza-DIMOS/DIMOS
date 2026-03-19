import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import requests

# Configurazione Simboli e Colori
SENSOR_DEFS = {
    "Elettrolivella": {"color": "#FF0000", "symbol": "square"},
    "Fessurimetro": {"color": "#00FF00", "symbol": "circle"},
    "Inclinometro": {"color": "#0000FF", "symbol": "diamond"},
    "Estensimetro": {"color": "#FFFF00", "symbol": "triangle-up"},
}

def search_location(query):
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}"
        headers = {'User-Agent': 'DIMOS_App'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except: return None
    return None

def render_territorial():
    st.subheader("🌍 Mappa Territoriale")
    
    if 'geo_sensors' not in st.session_state: st.session_state['geo_sensors'] = []
    if 'map_view' not in st.session_state: st.session_state['map_view'] = {"lat": 43.615, "lon": 13.518}

    # Barra di Ricerca
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        place = c1.text_input("Digita Città e premi VAI", key="search_txt")
        if c2.button("🔍 VAI", use_container_width=True):
            coords = search_location(place)
            if coords:
                st.session_state['map_view'] = {"lat": coords[0], "lon": coords[1]}
                st.rerun()

    # Creazione Mappa
    fig = go.Figure()
    
    # Aggiungi sensori esistenti
    if st.session_state['geo_sensors']:
        df = pd.DataFrame(st.session_state['geo_sensors'])
        for s_type, group in df.groupby("type"):
            fig.add_trace(go.Scattermapbox(
                lat=group["lat"], lon=group["lon"], mode='markers+text',
                marker=go.scattermapbox.Marker(size=18, color=SENSOR_DEFS[s_type]["color"]),
                text=group["name"], name=s_type, textposition="top right"
            ))

    fig.update_layout(
        mapbox=dict(style="open-street-map", center=st.session_state['map_view'], zoom=15),
        margin={"r":0,"t":0,"l":0,"b":0}, height=550, showlegend=True,
        clickmode='event+select',
        dragmode='lasso' # Forza la modalità selezione per catturare i punti
    )

    st.info("👆 Usa lo strumento 'Lasso' o 'Box Select' sulla mappa (in alto a dx nel grafico) o clicca su un punto, poi SALVA.")
    
    # Visualizzazione Mappa - Importante: 'selection_mode'
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="map_gis")

    # Pannello Input
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        s_id = col1.text_input("ID Sensore", placeholder="Es: Dimos-01", key="geo_id_in")
        s_tp = col2.selectbox("Tipo", list(SENSOR_DEFS.keys()), key="geo_tp_in")
        
        # Recupero coordinate
        sel_lat, sel_lon = None, None
        if event and "selection" in event and event["selection"]["points"]:
            sel_lat = event["selection"]["points"][0].get("lat")
            sel_lon = event["selection"]["points"][0].get("lon")
            if sel_lat:
                st.success(f"📍 Posizione agganciata: {sel_lat:.5f}, {sel_lon:.5f}")

        if col3.button("💾 SALVA", use_container_width=True):
            if sel_lat and s_id:
                st.session_state['geo_sensors'].append({"name": s_id, "type": s_tp, "lat": sel_lat, "lon": sel_lon})
                st.rerun()
            else:
                st.error("ERRORE: Devi cliccare un punto sulla mappa e dare un nome!")

def render_structural():
    st.subheader("🏗️ Layout su Foto")
    img_file = st.file_uploader("Carica immagine", type=["jpg", "png", "jpeg"])
    
    if img_file:
        if 'struc_sensors' not in st.session_state: st.session_state['struc_sensors'] = []
        img = Image.open(img_file)
        
        fig = px.imshow(img)
        
        if st.session_state['struc_sensors']:
            df = pd.DataFrame(st.session_state['struc_sensors'])
            for s_type, group in df.groupby("type"):
                fig.add_scatter(x=group["x"], y=group["y"], mode='markers+text',
                    marker=dict(color=SENSOR_DEFS[s_type]["color"], size=18, symbol=SENSOR_DEFS[s_type]["symbol"]),
                    text=group["name"], name=s_type, textposition="top center")

        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=600, clickmode='event+select', dragmode='drawpoint')
        
        st.info("👆 Clicca sulla foto per definire il punto, poi compila i dati e premi PIAZZA.")
        img_event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="img_struct")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            name = c1.text_input("ID", key="st_id_in")
            tipo = c2.selectbox("Tipo", list(SENSOR_DEFS.keys()), key="st_tp_in")
            
            x, y = None, None
            if img_event and "selection" in img_event and img_event["selection"]["points"]:
                x = img_event["selection"]["points"][0].get("x")
                y = img_event["selection"]["points"][0].get("y")
                st.success(f"📍 Coordinate: X={x}, Y={y}")

            if c3.button("🚩 PIAZZA", use_container_width=True):
                if x is not None and name:
                    st.session_state['struc_sensors'].append({"name": name, "x": x, "y": y, "type": tipo})
                    st.rerun()

def run_map_manager():
    t1, t2 = st.tabs(["🌍 GIS", "🖼️ FOTO"])
    with t1: render_territorial()
    with t2: render_structural()
