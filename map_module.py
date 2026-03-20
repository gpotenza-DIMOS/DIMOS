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
    st.header("🌍 Dashboard MAC Professionale")

    # Verifica Anagrafica
    if 'anagrafica' not in st.session_state:
        st.error("❌ Carica il file Excel nel Plotter per visualizzare i sensori.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- PANNELLO CONTROLLI (Sopra la mappa) ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore Attivo", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'])
        with c3:
            scale = st.number_input("Scala (Dimensione)", value=0.00200, format="%.5f", step=0.00005)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
        with c4:
            opac = st.slider("Trasp.", 0.0, 1.0, 0.4)

    # Impostazione centro mappa
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    # Inizializzazione Mappa
    m = folium.Map(location=st.session_state.center, zoom_start=18, tiles="OpenStreetMap")

    # --- LOGICA IMMAGINE (CORAZZATA) ---
    if up_img:
        try:
            # Caricamento e rotazione PIL
            img_pil = Image.open(up_img).convert("RGBA")
            if rot != 0:
                img_pil = img_pil.rotate(-rot, expand=True, resample=Image.BICUBIC)
            
            # Conversione in Base64 pulita
            buffer = BytesIO()
            img_pil.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            img_data = f"data:image/png;base64,{img_base64}"
            
            # Definizione confini (Bounds)
            lat, lon = st.session_state.center
            bounds = [[lat - scale, lon - scale * 1.5], [lat + scale, lon + scale * 1.5]]
            
            # Overlay
            ImageOverlay(
                image=img_data,
                bounds=bounds,
                opacity=opac,
                zindex=1,
                interactive=True
            ).add_to(m)
        except Exception as e:
            st.error(f"Errore caricamento immagine: {e}")

    # --- DISEGNO SENSORI ---
    for p in punti_salvati:
        is_target = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']],
            tooltip=p['nome'],
            icon=folium.Icon(color='blue' if is_target else 'red', icon='info-sign')
        ).add_to(m)

    # --- RENDER MAPPA ---
    st.info(f"📍 Per posizionare {target_selection}, clicca sul punto desiderato.")
    output = st_folium(m, width=1200, height=650, key="mac_v_final_top")

    # --- LOGICA SALVATAGGIO ---
    if output.get("last_clicked"):
        click_lat = output["last_clicked"]["lat"]
        click_lon = output["last_clicked"]["lng"]
        
        # Estrazione nomi
        dl_nome, sens_nome = target_selection.split(" | ")
        
        # Aggiorna database e salva
        nuovi_punti = [p for p in punti_salvati if p['nome'] != sens_nome]
        nuovi_punti.append({"nome": sens_nome, "lat": click_lat, "lon": click_lon, "dl": dl_nome})
        save_mac(nuovi_punti)
        st.rerun()

    # Riepilogo dati
    if punti_salvati:
        with st.expander("📄 Coordinate Salvate"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
