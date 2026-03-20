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
    st.header("🌍 Dashboard MAC - Mappa + Planimetria Dinamica")

    # 1. CARICAMENTO ANAGRAFICA
    if 'anagrafica' not in st.session_state:
        st.warning("⚠️ Carica l'Excel per attivare l'elenco sensori.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. CONTROLLI PARAMETRICI (Sopra la mappa) ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore da Posizionare", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        with c3:
            st.write("🔧 **Regolazioni Planimetria**")
            opac = st.slider("Opacità", 0.0, 1.0, 0.5)
            scale = st.slider("Dimensione (Scala)", 0.0001, 0.01, 0.002, format="%.4f")
            rot = st.slider("Rotazione (°)", -180, 180, 0)

    # --- 3. CONFIGURAZIONE MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189] # Default Ancona

    m = folium.Map(location=st.session_state.center, zoom_start=18)

    # Logica Overlay Immagine
    if up_img:
        img = Image.open(up_img)
        # Rotazione PIL prima dell'invio
        if rot != 0:
            img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Calcolo bordi dell'immagine basati sulla scala
        lat, lon = st.session_state.center
        bounds = [[lat - scale, lon - scale * 2], [lat + scale, lon + scale * 2]]
        
        # Aggiunta Overlay
        ImageOverlay(
            image=f"data:image/png;base64,{img_str}",
            bounds=bounds,
            opacity=opac,
            interactive=True,
            cross_origin=False,
            zindex=1 # Sopra la mappa, sotto i marker
        ).add_to(m)

    # 4. DISEGNO SENSORI
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=p['nome'],
            icon=folium.Icon(color='blue' if is_sel else 'red', icon='info-sign')
        ).add_to(m)

    # --- 5. RENDER E LOGICA CLICK ---
    st.info(f"📍 Stai posizionando: **{target_selection}** (Clicca sulla mappa o sulla planimetria)")
    output = st_folium(m, width=1300, height=650, key="mac_v5_final")

    if output.get("last_clicked"):
        lat_c, lon_c = output["last_clicked"]["lat"], output["last_clicked"]["lng"]
        dl_puro, nome_puro = target_selection.split(" | ")
        
        # Aggiorna database
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(punti_salvati)
        st.rerun()

    # Tabella di controllo
    if punti_salvati:
        with st.expander("📄 Riepilogo Coordinate"):
            st.table(pd.DataFrame(punti_salvati))
