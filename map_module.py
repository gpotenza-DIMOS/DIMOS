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
    with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=4)

def run_map_manager():
    st.header("🌍 Dashboard MAC - Mappa & Planimetria")

    if 'anagrafica' not in st.session_state:
        st.error("❌ Carica l'Excel nel Plotter per attivare i sensori.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- CONTROLLI SOPRA LA MAPPA ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore Attivo", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'])
        with c3:
            scale = st.number_input("Scala (Dimensione)", value=0.002, format="%.5f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
        with c4:
            opac = st.slider("Trasp.", 0.0, 1.0, 0.5)

    # --- MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    m = folium.Map(location=st.session_state.center, zoom_start=18)

    # GESTIONE IMMAGINE (Blindata)
    if up_img:
        try:
            img = Image.open(up_img).convert("RGBA")
            if rot != 0:
                img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
            
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            lat, lon = st.session_state.center
            # Bounding box semplificato e proporzionato
            bounds = [[lat - scale, lon - scale*1.5], [lat + scale, lon + scale*1.5]]
            
            ImageOverlay(
                image=f"data:image/png;base64,{img_str}",
                bounds=bounds,
                opacity=opac,
                zindex=1
            ).add_to(m)
        except Exception as e:
            st.error(f"Errore immagine: {e}")

    # MARKER
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']], 
            tooltip=p['nome'],
            icon=folium.Icon(color='blue' if is_sel else 'red')
        ).add_to(m)

    # RENDER
    st.info(f"📍 Clicca sulla mappa per posizionare: {target_selection}")
    output = st_folium(m, width=1200, height=600, key="mac_v_final")

    # SALVATAGGIO CLICK
    if output.get("last_clicked"):
        lat_c, lon_c = output["last_clicked"]["lat"], output["last_clicked"]["lng"]
        dl_puro, nome_puro = target_selection.split(" | ")
        
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(punti_salvati)
        st.rerun()
