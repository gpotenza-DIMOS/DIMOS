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

# --- FUNZIONI DI SERVIZIO (TUE) ---
def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_mac(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- MODULO PRINCIPALE ---
def run_map_manager():
    st.header("🌍 Dashboard MAC - Controllo Integrato")

    # 1. GESTIONE CARICAMENTO EXCEL (Sbloccata)
    # Se vuoi caricare un altro file, basta usare l'uploader qui sotto
    with st.expander("📂 Carica o Cambia File Excel", expanded='anagrafica' not in st.session_state):
        file_input = st.file_uploader("Trascina l'Excel qui (Foglio NAME)", type=['xlsx', 'xlsm'], key="new_excel_up")
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                ana = {}
                for c in range(1, df_n.shape[1]):
                    dl = str(df_n.iloc[0, c]).strip()
                    sn = str(df_n.iloc[1, c]).strip()
                    try:
                        la = float(df_n.iloc[3, c]) if df_n.iloc[3, c] != "" else None
                        lo = float(df_n.iloc[4, c]) if df_n.iloc[4, c] != "" else None
                    except: la, lo = None, None
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sn] = {"lat": la, "lon": lo}
                st.session_state['anagrafica'] = ana

    if 'anagrafica' not in st.session_state:
        st.info("Inizia caricando un file Excel.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. CONTROLLI PLANIMETRIA E SENSORI ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore da posizionare", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'])
        with c3:
            sc = st.number_input("Scala", value=0.0020, format="%.4f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
        with c4:
            if st.button("🗑️ Reset Dati", use_container_width=True):
                del st.session_state['anagrafica']
                st.rerun()

    # --- 3. GESTIONE MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    m = folium.Map(location=st.session_state.center, zoom_start=18)
    
    # Overlay Planimetria
    if up_img:
        try:
            img = Image.open(up_img).convert("RGBA")
            if rot != 0:
                img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            lat, lon = st.session_state.center
            b = [[lat - sc, lon - sc*1.5], [lat + sc, lon + sc*1.5]]
            ImageOverlay(image=f"data:image/png;base64,{img_b64}", bounds=b, opacity=0.5, zindex=1).add_to(m)
        except: pass

    # Marker
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker([p['lat'], p['lon']], icon=folium.Icon(color='blue' if is_sel else 'red')).add_to(m)

    # --- RENDER MAPPA (FIX PER KEYERROR) ---
    output = st_folium(m, width=1300, height=600, key="mac_map_final")

    # Gestione sicura del click
    if output and "last_clicked" in output and output["last_clicked"] is not None:
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        if target_selection:
            dl_puro, nome_puro = target_selection.split(" | ")
            punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
            punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
            save_mac(punti_salvati)
            st.rerun()
