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
        headers = {'User-Agent': 'DIMOS_MAC_V4'}
        response = requests.get(url, headers=headers).json()
        if response: return float(response[0]['lat']), float(response[0]['lon'])
    except: return None
    return None

def run_map_manager():
    st.header("🌍 Dashboard MAC - Mappa con Overlay Tecnico")

    # 1. RECUPERO ANAGRAFICA
    if 'anagrafica' not in st.session_state:
        st.warning("⚠️ Carica l'Excel per attivare i sensori.")
        file_input = st.file_uploader("📂 Carica Excel Monitoraggio", type=['xlsx', 'xlsm'])
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                ana = {}
                for c in range(1, df_n.shape[1]):
                    dl, sn = str(df_n.iloc[0, c]).strip(), str(df_n.iloc[1, c]).strip()
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

    # --- 2. DASHBOARD COMANDI (Sopra la mappa) ---
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
        with col2:
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore da Posizionare", opzioni)
        with col3:
            st.write("")
            if st.button("📥 Importa Excel", use_container_width=True):
                nuovi = [{"nome": s, "lat": c['lat'], "lon": c['lon'], "dl": d} for d in ana for s, c in ana[d].items() if c['lat']]
                save_mac(nuovi); st.rerun()

    # --- 3. GESTIONE OVERLAY IMMAGINE (Nuova Funzionalità) ---
    st.subheader("🖼️ Overlay Planimetria")
    exp_img = st.expander("Configura Immagine su Mappa", expanded=False)
    img_overlay = None
    
    with exp_img:
        up_img = st.file_uploader("Carica Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        c_ov1, c_ov2, c_ov3 = st.columns(3)
        with c_ov1:
            opac = st.slider("Opacità", 0.0, 1.0, 0.6)
            rot = st.slider("Rotazione (°) - *Simulata*", -180, 180, 0)
        with c_ov2:
            scale = st.slider("Scala Immagine", 0.0001, 0.01, 0.002, format="%.4f")
        with c_ov3:
            st.info("L'immagine verrà centrata sulla posizione attuale della mappa.")

    # --- 4. MAPPA ---
    if 'center' not in st.session_state: st.session_state.center = [43.6158, 13.5189]
    
    m = folium.Map(location=st.session_state.center, zoom_start=15)

    # Inserimento Immagine come Overlay
    if up_img:
        img = Image.open(up_img)
        # Se c'è rotazione, la applichiamo all'immagine prima di inviarla alla mappa
        if rot != 0:
            img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        img_url = f"data:image/png;base64,{img_str}"
        
        # Calcolo bordi (Bounding Box) in base alla scala
        lat, lon = st.session_state.center
        bounds = [[lat - scale, lon - scale*2], [lat + scale, lon + scale*2]]
        
        ImageOverlay(image=img_url, bounds=bounds, opacity=opac, interactive=True).add_to(m)

    # Marker Sensori
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker([p['lat'], p['lon']], tooltip=p['nome'],
                      icon=folium.Icon(color='blue' if is_sel else 'red')).add_to(m)

    # Render
    output = st_folium(m, width=1300, height=650, key="mac_overlay_map")

    # Salvataggio click
    if output.get("last_clicked"):
        lat_c, lon_c = output["last_clicked"]["lat"], output["last_clicked"]["lng"]
        dl_puro, nome_puro = target_selection.split(" | ")
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(punti_salvati); st.rerun()
