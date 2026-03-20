import streamlit as st
import pandas as pd
import json
import os
import requests
from streamlit_folium import st_folium
import folium
from folium.plugins import ImageOverlay
import base64
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
    st.header("🌍 Dashboard MAC - Mappa e Planimetria Integrata")

    # 1. RECUPERO ANAGRAFICA
    if 'anagrafica' not in st.session_state:
        st.warning("⚠️ Carica l'Excel nel Plotter o qui sotto per iniziare.")
        file_input = st.file_uploader("📂 Carica Excel NAME", type=['xlsx', 'xlsm'])
        if file_input:
            xls = pd.ExcelFile(file_input)
            df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
            ana = {}
            for c in range(1, df_n.shape[1]):
                dl, sn = str(df_n.iloc[0, c]).strip(), str(df_n.iloc[1, c]).strip()
                try:
                    la, lo = float(df_n.iloc[3, c]), float(df_n.iloc[4, c])
                except: la, lo = None, None
                if dl not in ana: ana[dl] = {}
                ana[dl][sn] = {"lat": la, "lon": lo}
            st.session_state['anagrafica'] = ana
            st.rerun()
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. DASHBOARD PARAMETRICA (Sopra la mappa) ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
        with c2:
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore da Posizionare", opzioni)
        with c3:
            # --- CONTROLLI IMMAGINE ---
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'])
        with c4:
            st.write("")
            if st.button("📥 Importa Excel"):
                nuovi = [{"nome": s, "lat": c['lat'], "lon": c['lon'], "dl": d} for d in ana for s, c in ana[d].items() if c['lat']]
                save_mac(nuovi); st.rerun()

    # --- 3. PARAMETRI DI SCALA E ROTAZIONE (Se l'immagine è caricata) ---
    overlay_params = {"opac": 0.5, "scale": 0.001, "rot": 0}
    if up_img:
        with st.expander("Adjust Planimetria (Scala / Rotazione / Trasparenza)", expanded=True):
            col_a, col_b, col_c = st.columns(3)
            overlay_params["opac"] = col_a.slider("Trasparenza", 0.0, 1.0, 0.5)
            overlay_params["scale"] = col_b.slider("Dimensione (Scala)", 0.0001, 0.0100, 0.0020, format="%.4f")
            overlay_params["rot"] = col_c.slider("Rotazione (°)", -180, 180, 0)

    # --- 4. CONFIGURAZIONE MAPPA ---
    if 'center' not in st.session_state: st.session_state.center = [43.6158, 13.5189]
    
    m = folium.Map(location=st.session_state.center, zoom_start=17)

    # Logica Overlay Immagine
    if up_img:
        img = Image.open(up_img)
        if overlay_params["rot"] != 0:
            img = img.rotate(-overlay_params["rot"], expand=True, resample=Image.BICUBIC)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Calcolo dell'area occupata dall'immagine
        lat, lon = st.session_state.center
        s = overlay_params["scale"]
        bounds = [[lat - s, lon - s*2], [lat + s, lon + s*2]]
        
        ImageOverlay(image=f"data:image/png;base64,{img_str}", bounds=bounds, opacity=overlay_params["opac"]).add_to(m)

    # Disegno Marker Sensori
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker([p['lat'], p['lon']], tooltip=p['nome'],
                      icon=folium.Icon(color='blue' if is_sel else 'red')).add_to(m)

    # Renderizzazione
    st.info(f"Clicca per piazzare: {target_selection}")
    output = st_folium(m, width=1200, height=600, key="mac_integrated_v4")

    # --- 5. SALVATAGGIO ---
    if output.get("last_clicked"):
        lat_c, lon_c = output["last_clicked"]["lat"], output["last_clicked"]["lng"]
        dl_puro, nome_puro = target_selection.split(" | ")
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(punti_salvati)
        st.rerun()

    if punti_salvati:
        with st.expander("Tabella Coordinate"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
