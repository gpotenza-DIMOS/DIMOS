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

# --- FUNZIONI ORIGINALI (PUNTO FERMO) ---
def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_mac(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_MAC_DASHBOARD'}
        response = requests.get(url, headers=headers).json()
        if response: return float(response[0]['lat']), float(response[0]['lon'])
    except: return None
    return None

# --- MODULO PRINCIPALE ---
def run_map_manager():
    st.header("🌍 Dashboard MAC - Controllo Integrato")

    if 'anagrafica' not in st.session_state:
        st.warning("⚠️ Nessun dato caricato. Carica l'Excel per attivare la mappa.")
        file_input = st.file_uploader("📂 Carica Excel Monitoraggio", type=['xlsx', 'xlsm'])
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
                st.rerun()
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- CONTROLLI (SOPRA LA MAPPA) ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Planimetria", type=['png', 'jpg', 'jpeg'])
        with c3:
            scale = st.number_input("Scala", value=0.002, format="%.5f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
        with c4:
            opac = st.slider("Trasp.", 0.0, 1.0, 0.5)

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
            bounds = [[lat - scale, lon - scale*1.5], [lat + scale, lon + scale*1.5]]
            ImageOverlay(image=f"data:image/png;base64,{img_b64}", bounds=bounds, opacity=opac, zindex=1).add_to(m)
        except: pass

    # Marker
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker([p['lat'], p['lon']], icon=folium.Icon(color='blue' if is_sel else 'red')).add_to(m)

    # --- RENDER E FIX KEYERROR ---
    output = st_folium(m, width=1300, height=600, key="mac_main_dashboard")

    # Controllo sicuro: se 'last_clicked' non c'è, output.get non crasha
    click_data = output.get("last_clicked") if output else None
    
    if click_data:
        lat_c, lon_c = click_data["lat"], click_data["lng"]
        if target_selection and " | " in target_selection:
            dl_puro, nome_puro = target_selection.split(" | ")
            punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
            punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
            save_mac(punti_salvati)
            st.rerun()
