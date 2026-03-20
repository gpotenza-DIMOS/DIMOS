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
    st.header("🌍 Dashboard MAC - Operativa")

    # 1. Controllo Anagrafica (Senza crash)
    if 'anagrafica' not in st.session_state:
        st.info("👋 Carica il file Excel nel modulo Plotter per vedere i sensori.")
        # Se vogliamo caricare anche qui:
        up_ex = st.file_uploader("In alternativa, carica Excel qui", type=['xlsx', 'xlsm'], key="map_ex")
        if up_ex:
            # Logica minima di caricamento se serve...
            pass
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. CONTROLLI SOPRA LA MAPPA ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore da piazzare", opzioni if opzioni else ["Nessun Sensore"])
        with c2:
            up_img = st.file_uploader("🖼️ Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        with c3:
            scale = st.number_input("Scala", value=0.002, format="%.5f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
        with c4:
            opac = st.slider("Trasp.", 0.0, 1.0, 0.5)

    # --- 3. MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    m = folium.Map(location=st.session_state.center, zoom_start=18)

    # Gestione Immagine
    if up_img:
        try:
            img = Image.open(up_img).convert("RGBA")
            if rot != 0:
                img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            
            lat, lon = st.session_state.center
            bounds = [[lat - scale, lon - scale*1.5], [lat + scale, lon + scale*1.5]]
            ImageOverlay(image=f"data:image/png;base64,{img_b64}", bounds=bounds, opacity=opac, zindex=1).add_to(m)
        except: st.error("Errore nel rendering immagine")

    # Disegno Marker Esistenti
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker([p['lat'], p['lon']], tooltip=p['nome'],
                      icon=folium.Icon(color='blue' if is_sel else 'red')).add_to(m)

    # --- 4. RENDER (FIX ERRORI) ---
    output = st_folium(m, width=1200, height=600, key="mac_map_stable")

    # Logica Click sicura: controlliamo che 'last_clicked' esista E non sia nullo
    if output and "last_clicked" in output and output["last_clicked"] is not None:
        # Verifichiamo se il click è "nuovo" per evitare loop infiniti di rerun
        click_lat = output["last_clicked"]["lat"]
        click_lon = output["last_clicked"]["lng"]
        
        # Salviamo solo se abbiamo un sensore selezionato validamente
        if target_selection and " | " in target_selection:
            dl_puro, nome_puro = target_selection.split(" | ")
            
            # Evitiamo di salvare se le coordinate sono identiche all'ultimo punto (previene loop)
            punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
            punti_salvati.append({"nome": nome_puro, "lat": click_lat, "lon": click_lon, "dl": dl_puro})
            save_mac(punti_salvati)
            st.rerun()

    # Tabella dati a scomparsa
    if punti_salvati:
        with st.expander("Dati salvati"):
            st.dataframe(pd.DataFrame(punti_salvati))
