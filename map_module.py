import streamlit as st
import pandas as pd
import json
import os
import base64
from streamlit_folium import st_folium
import folium
from folium.plugins import ImageOverlay
from PIL import Image
from io import BytesIO

CONFIG_FILE = "mac_positions.json"

def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_mac(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def run_map_manager():
    st.header("🌍 Dashboard MAC - Controllo Reale")

    # 1. RECUPERO DATI (Se non ci sono, non partiamo neanche)
    if 'anagrafica' not in st.session_state:
        st.error("❌ Errore: Carica prima il file Excel nel modulo Plotter.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. CONTROLLI SOPRA LA MAPPA ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore da piazzare", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'])
        with c3:
            opac = st.slider("Trasparenza", 0.0, 1.0, 0.4)
            scale = st.slider("Dimensione", 0.0001, 0.01, 0.002, format="%.4f")
            rot = st.slider("Rotazione (°)", -180, 180, 0)

    # --- 3. MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189] # Default Ancona

    m = folium.Map(location=st.session_state.center, zoom_start=18, tiles="OpenStreetMap")

    # Gestione Planimetria
    if up_img:
        try:
            img = Image.open(up_img).convert("RGBA")
            if rot != 0:
                img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
            
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Posizionamento
            lat, lon = st.session_state.center
            bounds = [[lat - scale, lon - scale*2], [lat + scale, lon + scale*2]]
            
            ImageOverlay(
                image=f"data:image/png;base64,{img_base64}",
                bounds=bounds,
                opacity=opac,
                zindex=1
            ).add_to(m)
        except Exception as e:
            st.error(f"Errore caricamento immagine: {e}")

    # Marker
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']], 
            tooltip=p['nome'],
            icon=folium.Icon(color='blue' if is_sel else 'red')
        ).add_to(m)

    # Render
    st.info(f"Clicca per posizionare: {target_selection}")
    output = st_folium(m, width=1200, height=600, key="mac_v6_stable")

    # --- 4. SALVATAGGIO ---
    if output.get("last_clicked"):
        lat_c, lon_c = output["last_clicked"]["lat"], output["last_clicked"]["lng"]
        dl_puro, nome_puro = target_selection.split(" | ")
        
        # Pulizia e inserimento
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(punti_salvati)
        st.rerun()
