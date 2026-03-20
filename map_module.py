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
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except:
        return None
    return None


# --- MODULO PRINCIPALE ---
def run_map_manager():
    st.header("🌍 Dashboard MAC - Controllo Integrato")

    # --- CARICAMENTO EXCEL ---
    if 'anagrafica' not in st.session_state:
        st.warning("⚠️ Nessun dato caricato.")
        file_input = st.file_uploader("📂 Carica Excel (Foglio NAME)", type=['xlsx', 'xlsm'])
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
                    except:
                        la, lo = None, None
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sn] = {"lat": la, "lon": lo}
                st.session_state['anagrafica'] = ana
                st.rerun()
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- CONTROL PANEL ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])

        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))

        with c2:
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Sensore", opzioni)

        with c3:
            if st.button("📥 Importa da Excel"):
                nuovi = []
                for d in ana:
                    for s, c in ana[d].items():
                        if c['lat'] and c['lon']:
                            nuovi.append({"nome": s, "lat": c['lat'], "lon": c['lon'], "dl": d})
                save_mac(nuovi)
                st.rerun()

    # --- PLANIMETRIA CONTROLLI ---
    with st.expander("🖼️ Overlay Planimetria"):
        up_img = st.file_uploader("Carica immagine", type=['png', 'jpg', 'jpeg'])

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            scale = st.slider("Scala", 0.0001, 0.01, 0.002, 0.0001)
        with col_b:
            rotation = st.slider("Rotazione", -180, 180, 0)
        with col_c:
            opacity = st.slider("Trasparenza", 0.0, 1.0, 0.5)

    # --- MAPPA ---
    if 'center' not in st.session_state:
        if punti_salvati:
            st.session_state.center = [punti_salvati[0]['lat'], punti_salvati[0]['lon']]
        else:
            st.session_state.center = [43.6158, 13.5189]

    search = st.text_input("🔍 Cerca città")
    if search:
        coords = get_coords(search)
        if coords:
            st.session_state.center = coords

    m = folium.Map(location=st.session_state.center, zoom_start=18)

    # --- OVERLAY IMMAGINE ---
    if up_img:
        try:
            img = Image.open(up_img).convert("RGBA")

            if rotation != 0:
                img = img.rotate(-rotation, expand=True)

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_b64 = base64.b64encode(buffer.getvalue()).decode()

            lat, lon = st.session_state.center

            bounds = [
                [lat - scale, lon - scale],
                [lat + scale, lon + scale]
            ]

            ImageOverlay(
                image=f"data:image/png;base64,{img_b64}",
                bounds=bounds,
                opacity=opacity
            ).add_to(m)

        except Exception as e:
            st.error(f"Errore immagine: {e}")

    # --- MARKER ---
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']],
            popup=f"{p['dl']} - {p['nome']}",
            icon=folium.Icon(color='blue' if is_sel else 'red')
        ).add_to(m)

    # --- RENDER ---
    output = st_folium(m, width=1300, height=600)

    # --- CLICK SALVATAGGIO ---
    if output and output.get("last_clicked") and target_selection:
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]

        if " | " in target_selection:
            dl_puro, nome_puro = target_selection.split(" | ")

            punti_salvati = [
                p for p in punti_salvati
                if not (p['nome'] == nome_puro and p['dl'] == dl_puro)
            ]

            punti_salvati.append({
                "nome": nome_puro,
                "lat": lat_c,
                "lon": lon_c,
                "dl": dl_puro
            })

            save_mac(punti_salvati)
            st.rerun()

    # --- TABELLA ---
    if punti_salvati:
        with st.expander("📄 Coordinate"):
            st.dataframe(pd.DataFrame(punti_salvati))
            if st.button("🗑️ Reset"):
                save_mac([])
                st.rerun()
