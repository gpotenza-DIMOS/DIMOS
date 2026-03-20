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
    st.header("🌍 Dashboard MAC - Sistema Professionale")

    # 1. RECUPERO DATI (Blindato)
    if 'anagrafica' not in st.session_state:
        st.error("❌ Dati mancanti! Carica il file Excel nel modulo Plotter prima di usare la mappa.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. PANNELLO CONTROLLI ORIZZONTALE ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            sel_dls = st.multiselect("📡 Filtra Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore Attivo", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        with c3:
            st.markdown("**Regolazioni Immagine**")
            opac = st.slider("Trasparenza", 0.0, 1.0, 0.5)
            # Scala logaritmica per maggior precisione
            scale = st.number_input("Scala (Zoom Immagine)", value=0.002, format="%.5f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)

    # --- 3. GESTIONE MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    m = folium.Map(location=st.session_state.center, zoom_start=18, tiles="OpenStreetMap")

    # Logica Overlay (Questa volta senza errori di rendering)
    if up_img:
        try:
            raw_img = Image.open(up_img).convert("RGBA")
            # Ruotiamo l'immagine se necessario
            if rot != 0:
                raw_img = raw_img.rotate(-rot, expand=True, resample=Image.BICUBIC)
            
            # Convertiamo per Folium
            buffered = BytesIO()
            raw_img.save(buffered, format="PNG")
            img_64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Calcolo dei confini basato sul centro e la scala scelta
            lat, lon = st.session_state.center
            # Il rapporto 2:1 (lon:lat) corregge la distorsione della proiezione Mercatore
            bounds = [[lat - scale, lon - scale*1.5], [lat + scale, lon + scale*1.5]]
            
            ImageOverlay(
                image=f"data:image/png;base64,{img_64}",
                bounds=bounds,
                opacity=opac,
                zindex=1,
                name="Planimetria Tecnica"
            ).add_to(m)
        except Exception as e:
            st.error(f"Errore tecnico immagine: {e}")

    # Disegno Marker
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=f"<b>{p['nome']}</b>",
            icon=folium.Icon(color='blue' if is_sel else 'red', icon='info-sign')
        ).add_to(m)

    # --- 4. RENDER E SALVATAGGIO ---
    st.info(f"📍 PUNTA E CLICCA: Posiziona il sensore **{target_selection}**")
    
    # Visualizziamo la mappa
    output = st_folium(m, width=1200, height=650, key="mac_v_final_top")

    # Cattura del click per salvare le coordinate
    if output.get("last_clicked"):
        new_lat, new_lon = output["last_clicked"]["lat"], output["last_clicked"]["lng"]
        dl_puro, nome_puro = target_selection.split(" | ")
        
        # Aggiorna il DB JSON
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": new_lat, "lon": new_lon, "dl": dl_puro})
        save_mac(punti_salvati)
        st.rerun()

    # Visualizzazione tabella per conferma
    if punti_salvati:
        with st.expander("📄 Elenco Coordinate Salvate"):
            st.table(pd.DataFrame(punti_salvati))
