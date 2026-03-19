import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import requests

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

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        place = c1.text_input("Digita Città e premi VAI", key="search_txt")
        if c2.button("🔍 VAI", use_container_width=True):
            coords = search_location(place)
            if coords:
                st.session_state['map_view'] = {"lat": coords[0], "lon": coords[1]}
                st.rerun()

    fig = go.Figure()
    if st.session_state['geo_sensors']:
        df = pd.DataFrame(st.session_state['geo_sensors'])
        for s_type, group in df.groupby("type"):
            fig.add_trace(go.Scattermapbox(
                lat=group["lat"], lon=group["lon"], mode='markers+text',
                marker=go.scattermapbox.Marker(size=15, color=SENSOR_DEFS[s_type]["color"]),
                text=group["name"], name=s_type, textposition="top right"
            ))

    fig.update_layout(
        mapbox=dict(style="open-street-map", center=st.session_state['map_view'], zoom=14),
        margin={"r":0,"t":0,"l":0,"b":0}, height=500, showlegend=True,
        clickmode='event+select'
    )

    st.info("👆 Clicca sulla mappa, poi compila ID e Tipo qui sotto e premi SALVA.")
    # Catturiamo i dati della selezione/click
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="geo_map")

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        s_id = col1.text_input("ID Sensore", placeholder="es. Dimos-01", key="input_geo_id")
        s_tp = col2.selectbox("Tipo", list(SENSOR_DEFS.keys()), key="input_geo_tp")
        
        # LOGICA DI ESTRAZIONE COORDINATE
        current_lat, current_lon = None, None
        if event and "selection" in event and event["selection"]["points"]:
            current_lat = event["selection"]["points"][0]["lat"]
            current_lon = event["selection"]["points"][0]["lon"]
            st.write(f"📍 Punto selezionato: **{current_lat:.5f}, {current_lon:.5f}**")

        if col3.button("💾 SALVA", use_container_width=True):
            if current_lat and s_id:
                st.session_state['geo_sensors'].append({"name": s_id, "type": s_tp, "lat": current_lat, "lon": current_lon})
                st.rerun()
            else:
                st.warning("Clicca sulla mappa prima di salvare!")

def render_structural():
    st.subheader("🏗️ Layout su Foto")
    img_file = st.file_uploader("Carica immagine", type=["jpg", "png", "jpeg"])
    
    if img_file:
        if 'struc_sensors' not in st.session_state: st.session_state['struc_sensors'] = []
        img = Image.open(img_file)
        
        # Usiamo go.Figure per avere più controllo rispetto a px.imshow
        fig = go.Figure()
        fig.add_trace(go.Image(z=img))
        
        if st.session_state['struc_sensors']:
            df = pd.DataFrame(st.session_state['struc_sensors'])
            for s_type, group in df.groupby("type"):
                fig.add_trace(go.Scatter(
                    x=group["x"], y=group["y"], mode='markers+text',
                    marker=dict(color=SENSOR_DEFS[s_type]["color"], size=15, symbol=SENSOR_DEFS[s_type]["symbol"]),
                    text=group["name"], name=s_type, textposition="top center"
                ))

        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=600, clickmode='event+select')
        
        st.info("👆 Clicca sulla foto, compila i dati e premi PIAZZA.")
        img_event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="struct_img")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            name = c1.text_input("ID", key="input_st_id")
            tipo = c2.selectbox("Tipo", list(SENSOR_DEFS.keys()), key="input_st_tp")
            
            curr_x, curr_y = None, None
            if img_event and "selection" in img_event and img_event["selection"]["points"]:
                curr_x = img_event["selection"]["points"][0]["x"]
                curr_y = img_event["selection"]["points"][0]["y"]
                st.write(f"📍 Coordinate click: **X={curr_x}, Y={curr_y}**")

            if c3.button("🚩 PIAZZA", use_container_width=True):
                if curr_x is not None and name:
                    st.session_state['struc_sensors'].append({"name": name, "x": curr_x, "y": curr_y, "type": tipo})
                    st.rerun()
                else:
                    st.warning("Clicca sulla foto e inserisci un ID!")

def run_map_manager():
    t1, t2 = st.tabs(["🌍 GIS", "🖼️ FOTO"])
    with t1: render_territorial()
    with t2: render_structural()
