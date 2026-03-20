import streamlit as st
import pandas as pd
import json
import os
import requests
import base64
from streamlit_folium import st_folium
import folium
from folium.raster_layers import ImageOverlay
from PIL import Image
from io import BytesIO

CONFIG_FILE = "mac_positions.json"
OVERLAY_FILE = "overlay_config.json"

# ------------------ FILE UTILS ------------------
def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ------------------ GEO ------------------
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_MAC'}
        res = requests.get(url, headers=headers).json()
        if res:
            return float(res[0]['lat']), float(res[0]['lon'])
    except:
        return None
    return None

# ------------------ EXCEL ------------------
def parse_excel(file):
    xls = pd.ExcelFile(file)
    if "NAME" not in xls.sheet_names:
        return None

    df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
    ana = {}

    for c in range(1, df.shape[1]):
        dl = str(df.iloc[0, c]).strip()
        sn = str(df.iloc[1, c]).strip()

        try:
            lat = float(df.iloc[3, c]) if df.iloc[3, c] != "" else None
            lon = float(df.iloc[4, c]) if df.iloc[4, c] != "" else None
        except:
            lat, lon = None, None

        if dl not in ana:
            ana[dl] = {}

        ana[dl][sn] = {"lat": lat, "lon": lon}

    return ana


# ------------------ MAIN ------------------
def run_map_manager():

    st.title("🌍 Dashboard MAC PRO")

    # ----------- EXCEL MANAGER -----------
    with st.expander("📂 Gestione Excel", expanded='anagrafica' not in st.session_state):

        file_input = st.file_uploader("Carica Excel (Foglio NAME)", type=['xlsx','xlsm'])

        if file_input:
            ana = parse_excel(file_input)
            if ana:
                st.session_state['anagrafica'] = ana
                st.success("Excel caricato")
            else:
                st.error("Foglio NAME non trovato")

        if 'anagrafica' in st.session_state:
            if st.button("🔄 Cambia Excel"):
                del st.session_state['anagrafica']
                st.rerun()

    if 'anagrafica' not in st.session_state:
        st.stop()

    ana = st.session_state['anagrafica']
    punti = load_json(CONFIG_FILE) or []

    # ----------- CONTROLLI -----------
    col1, col2 = st.columns(2)

    with col1:
        sel_dls = st.multiselect("Datalogger", list(ana.keys()), default=list(ana.keys()))

    with col2:
        sensori = [f"{d} | {s}" for d in sel_dls for s in ana[d]]
        target = st.selectbox("Sensore", sensori)

    # ----------- OVERLAY SETTINGS -----------
    overlay = load_json(OVERLAY_FILE) or {}

    with st.expander("🖼️ Overlay Planimetria (tipo GIS)"):
        img_file = st.file_uploader("Carica immagine", type=["png","jpg","jpeg"])

        scale = st.slider("Scala", 0.0001, 0.02, overlay.get("scale",0.002))
        rotation = st.slider("Rotazione", -180, 180, overlay.get("rotation",0))
        opacity = st.slider("Trasparenza", 0.0, 1.0, overlay.get("opacity",0.5))

        if st.button("💾 Salva configurazione overlay"):
            save_json(OVERLAY_FILE, {
                "scale": scale,
                "rotation": rotation,
                "opacity": opacity
            })
            st.success("Salvato")

    # ----------- MAPPA -----------
    if 'center' not in st.session_state:
        if punti:
            st.session_state.center = [punti[0]['lat'], punti[0]['lon']]
        else:
            st.session_state.center = [45.4642, 9.1900]

    city = st.text_input("🔍 Cerca città")
    if city:
        coords = get_coords(city)
        if coords:
            st.session_state.center = coords

    m = folium.Map(location=st.session_state.center, zoom_start=18)

    # ----------- OVERLAY IMAGE -----------
    if img_file:
        try:
            img = Image.open(img_file).convert("RGBA")

            if rotation != 0:
                img = img.rotate(-rotation, expand=True)

            buf = BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            lat, lon = st.session_state.center

            bounds = [
                [lat - scale, lon - scale],
                [lat + scale, lon + scale]
            ]

            ImageOverlay(
                image=f"data:image/png;base64,{b64}",
                bounds=bounds,
                opacity=opacity
            ).add_to(m)

        except Exception as e:
            st.error(e)

    # ----------- MARKER -----------
    for p in punti:
        is_sel = target and p['nome'] in target

        folium.Marker(
            [p['lat'], p['lon']],
            popup=f"{p['dl']} - {p['nome']}",
            icon=folium.Icon(color='blue' if is_sel else 'red')
        ).add_to(m)

    # ----------- RENDER -----------
    out = st_folium(m, width=1400, height=650)

    # ----------- CLICK SAVE -----------
    if out and out.get("last_clicked") and target:

        lat = out["last_clicked"]["lat"]
        lon = out["last_clicked"]["lng"]

        dl, nome = target.split(" | ")

        punti = [
            p for p in punti
            if not (p['nome']==nome and p['dl']==dl)
        ]

        punti.append({
            "nome": nome,
            "lat": lat,
            "lon": lon,
            "dl": dl
        })

        save_json(CONFIG_FILE, punti)
        st.rerun()

    # ----------- TABLE -----------
    with st.expander("📄 Dati"):
        st.dataframe(pd.DataFrame(punti))

        if st.button("🗑 Reset"):
            save_json(CONFIG_FILE, [])
            st.rerun()
