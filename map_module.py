import streamlit as st
import pandas as pd
import json
import os
import requests
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
    st.header("🌍 Dashboard MAC - Controllo Integrato")

    # --- 1. GESTIONE EXCEL (Sbloccata) ---
    with st.expander("📂 Gestione File Excel", expanded='anagrafica' not in st.session_state):
        file_input = st.file_uploader("Carica Excel Monitoraggio (Foglio NAME)", type=['xlsx', 'xlsm'])
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                ana = {}
                for c in range(1, df_n.shape[1]):
                    dl = str(df_n.iloc[0, c]).strip()
                    sn = str(df_n.iloc[1, c]).strip()
                    try:
                        la = float(df_n.iloc[3, c]); lo = float(df_n.iloc[4, c])
                    except: la, lo = None, None
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sn] = {"lat": la, "lon": lo}
                st.session_state['anagrafica'] = ana
        
        if st.button("🗑️ Reset Dati Sessione"):
            if 'anagrafica' in st.session_state: del st.session_state['anagrafica']
            st.rerun()

    if 'anagrafica' not in st.session_state:
        st.info("Carica un file Excel per procedere.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. CONTROLLI PLANIMETRIA E SENSORI ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'])
        with c3:
            sc = st.number_input("Scala", value=0.002, format="%.5f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
        with c4:
            opac = st.slider("Trasp.", 0.0, 1.0, 0.5)

    # --- 3. MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    m = folium.Map(location=st.session_state.center, zoom_start=18)
    
    # Overlay Immagine
    if up_img:
        try:
            img = Image.open(up_img).convert("RGBA")
            if rot != 0: img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
            buf = BytesIO(); img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            lat, lon = st.session_state.center
            b = [[lat - sc, lon - sc*1.5], [lat + sc, lon + sc*1.5]]
            ImageOverlay(image=f"data:image/png;base64,{img_b64}", bounds=b, opacity=opac, zindex=1).add_to(m)
        except: pass

    # Marker
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker([p['lat'], p['lon']], icon=folium.Icon(color='blue' if is_sel else 'red')).add_to(m)

    # Render Mappa - QUI IL FIX PER L'ERRORE
    output = st_folium(m, width=1300, height=600, key="mac_v_final")

    # --- 4. SALVATAGGIO AL CLICK (Senza KeyError) ---
    if output and output.get("last_clicked"):
        click = output["last_clicked"]
        if target_selection:
            dl_puro, nome_puro = target_selection.split(" | ")
            punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
            punti_salvati.append({"nome": nome_puro, "lat": click["lat"], "lon": click["lng"], "dl": dl_puro})
            save_mac(punti_salvati)
            st.rerun()
