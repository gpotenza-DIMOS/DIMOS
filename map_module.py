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

# --- FUNZIONI DI SERVIZIO ---
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

    # --- 1. SEZIONE CARICAMENTO (SBLOCCATA) ---
    with st.expander("📂 Caricamento Dati ed Excel", expanded='anagrafica' not in st.session_state):
        c1, c2 = st.columns([3, 1])
        with c1:
            file_input = st.file_uploader("Carica Excel Monitoraggio (NAME)", type=['xlsx', 'xlsm'], key="main_excel")
        with c2:
            if st.button("🗑️ Reset Dati", use_container_width=True):
                if 'anagrafica' in st.session_state:
                    del st.session_state['anagrafica']
                st.rerun()

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

    # --- 2. PANNELLO DI CONTROLLO (IMMAGINE + SENSORI) ---
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            sel_dls = st.multiselect("📡 Filtra Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni_sensori = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Seleziona Sensore", opzioni_sensori)
        
        with col2:
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'], key="plan_upload")
        
        with col3:
            sc = st.number_input("Scala Planimetria", value=0.0020, format="%.4f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
            opac = st.slider("Trasparenza", 0.0, 1.0, 0.5)

    # --- 3. MAPPA ---
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
            ImageOverlay(image=f"data:image/png;base64,{img_b64}", bounds=b, opacity=opac, zindex=1).add_to(m)
        except Exception as e:
            st.error(f"Errore immagine: {e}")

    # Marker
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']], 
            tooltip=p['nome'],
            icon=folium.Icon(color='blue' if is_sel else 'red', icon='info-sign')
        ).add_to(m)

    # Render Mappa (con protezione KeyError)
    output = st_folium(m, width=1300, height=600, key="mac_map_final")

    # --- 4. SALVATAGGIO ---
    if output and output.get("last_clicked"):
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        if target_selection and " | " in target_selection:
            dl_puro, nome_puro = target_selection.split(" | ")
            punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
            punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
            save_mac(punti_salvati)
            st.rerun()

    if punti_salvati:
        with st.expander("📄 Coordinate"):
            st.dataframe(pd.DataFrame(punti_salvati))
