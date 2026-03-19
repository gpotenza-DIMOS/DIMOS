import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import io

# Configurazione Categorie
SENSOR_DEFS = {
    "Elettrolivella": {"color": "#FF0000", "symbol": "square"},
    "Fessurimetro": {"color": "#00FF00", "symbol": "circle"},
    "Inclinometro": {"color": "#0000FF", "symbol": "diamond"},
    "Estensimetro": {"color": "#FFFF00", "symbol": "triangle-up"},
}

def render_territorial():
    st.subheader("🌍 Navigazione e Monitoraggio Territoriale")
    
    if 'geo_sensors' not in st.session_state:
        st.session_state['geo_sensors'] = []

    # 1. BARRA DI RICERCA / NAVIGAZIONE
    with st.expander("🔍 Ricerca Località o Coordinate", expanded=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        search_city = c1.text_input("Inserisci Città o Indirizzo (es: Campi Bisenzio)")
        set_lat = c2.number_input("Latitudine", value=43.8248, format="%.6f")
        set_lon = c3.number_input("Longitudine", value=11.1222, format="%.6f")
        
        # Nota: Qui andrebbe integrato un geocoder (geopy) per rendere la ricerca testo reale.
        # Per ora usiamo i campi numerici come "navigatore" manuale.

    # 2. MAPPA INTERATTIVA
    fig = go.Figure()

    # Aggiungiamo i sensori salvati
    if st.session_state['geo_sensors']:
        df = pd.DataFrame(st.session_state['geo_sensors'])
        for s_type, group in df.groupby("type"):
            fig.add_trace(go.Scattermapbox(
                lat=group["lat"], lon=group["lon"],
                mode='markers+text',
                marker=go.scattermapbox.Marker(
                    size=15, 
                    color=SENSOR_DEFS[s_type]["color"]
                ),
                text=group["name"],
                name=s_type
            ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=set_lat, lon=set_lon),
            zoom=14
        ),
        margin={"r":0,"t":0,"l":0,"b":0},
        height=600,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # 3. PANNELLO DI AGGIUNTA MANUALE
    st.markdown("---")
    st.markdown("#### 📍 Aggiungi Sensore nella posizione corrente")
    col1, col2, col3 = st.columns([2, 2, 1])
    new_name = col1.text_input("ID Sensore", placeholder="S-01")
    new_type = col2.selectbox("Tipo Sensore", list(SENSOR_DEFS.keys()))
    
    if col3.button("CONFERMA POSIZIONE", use_container_width=True):
        st.session_state['geo_sensors'].append({
            "name": new_name,
            "type": new_type,
            "lat": set_lat,
            "lon": set_lon
        })
        st.success(f"Sensore {new_name} posizionato!")
        st.rerun()

def render_structural():
    st.subheader("🖼️ Layout Strutturale su Foto")
    
    img_file = st.file_uploader("Carica immagine", type=["jpg", "png", "jpeg"])
    
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

        if st.session_state['struc_sensors']:
            df = pd.DataFrame(st.session_state['struc_sensors'])
            for s_type, group in df.groupby("type"):
                fig.add_trace(go.Scatter(
                    x=group["x"], y=group["y"], mode='markers+text',
                    marker=dict(
                        color=SENSOR_DEFS[s_type]["color"], 
                        size=18, 
                        symbol=SENSOR_DEFS[s_type]["symbol"]
                    ),
                    text=group["name"], textposition="top center", name=s_type
                ))

        fig.update_xaxes(range=[0, width], visible=False)
        fig.update_yaxes(range=[0, height], visible=False, scaleanchor="x")
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=600)

        # Visualizziamo e permettiamo di leggere le coordinate al passaggio del mouse
        st.plotly_chart(fig, use_container_width=True)

        with st.container(border=True):
            st.write("Inserisci le coordinate X e Y lette dall'immagine:")
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
            n = c1.text_input("ID", key="s_id")
            t = c2.selectbox("Tipo", list(SENSOR_DEFS.keys()), key="s_tp")
            x = c3.number_input("X", value=0)
            y = c4.number_input("Y", value=0)
            if c5.button("PIAZZA", use_container_width=True):
                st.session_state['struc_sensors'].append({"name": n, "x": x, "y": y, "type": t})
                st.rerun()

def run_map_manager():
    t1, t2 = st.tabs(["🌍 MAPPA GIS", "🖼️ LAYOUT STRUTTURA"])
    with t1: render_territorial()
    with t2: render_structural()
