import streamlit as st
import pandas as pd
import json
import os
import folium
from folium.features import DivIcon
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
import re
from PIL import Image
import base64
import io
import math

CONFIG_FILE = "mac_positions.json"

# ----------------- UTILS -----------------
def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except: return {}
    return {}

def save_mac(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def parse_web_name(web_name):
    unit = re.findall(r'\[(.*?)\]', web_name)
    unit = unit[0] if unit else ""
    clean_name = re.sub(r'\[.*?\]', '', web_name).strip()
    parts = clean_name.split()
    dl = parts[0] if len(parts) > 0 else "UNKNOWN_DL"
    full_sensor = parts[1] if len(parts) > 1 else "UNKNOWN_SENSOR"
    sensor_parts = full_sensor.split('_')
    if len(sensor_parts) > 2:
        sn = "_".join(sensor_parts[:-1])
        param = sensor_parts[-1]
    else:
        sn = full_sensor
        param = "Dato"
    return dl, sn, param, unit

def parse_excel_advanced(file):
    xls = pd.ExcelFile(file)
    df = pd.read_excel(xls, sheet_name="NAME" if "NAME" in xls.sheet_names else 0, header=None).fillna("")
    ana = {}
    for c in range(1, df.shape[1]):
        dl_raw = str(df.iloc[0, c]).strip()
        sn_raw = str(df.iloc[1, c]).strip()
        web_name = str(df.iloc[2, c]).strip()
        dl_web, sn_web, param, unit = parse_web_name(web_name)
        dl = dl_raw if dl_raw else dl_web
        sn = sn_raw if sn_raw else sn_web
        try:
            lat = float(df.iloc[3, c]) if df.iloc[3, c] != "" else None
            lon = float(df.iloc[4, c]) if df.iloc[4, c] != "" else None
        except: lat, lon = None, None
        if dl not in ana: ana[dl] = {}
        if sn not in ana[dl]:
            ana[dl][sn] = {"lat": lat, "lon": lon, "params": []}
        param_full = f"{param} [{unit}]"
        if param_full not in ana[dl][sn]["params"]:
            ana[dl][sn]["params"].append(param_full)
    return ana

def get_rotated_corners(center_lat, center_lon, width_m, height_m, rotation_deg):
    """Calcola i 4 angoli di un rettangolo ruotato (approssimazione metrica locale)"""
    # Conversione approssimativa metri -> gradi
    deg_lat = height_m / 111132.0
    deg_lon = width_m / (111132.0 * math.cos(math.radians(center_lat)))
    
    angle = math.radians(rotation_deg)
    corners = []
    # Offset dei 4 angoli rispetto al centro
    for dx, dy in [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]:
        # Rotazione
        rx = dx * deg_lon * math.cos(angle) - dy * deg_lat * math.sin(angle)
        ry = dx * deg_lon * math.sin(angle) + dy * deg_lat * math.cos(angle)
        corners.append([center_lat + ry, center_lon + rx])
    return corners

# ----------------- MAIN -----------------
def run_map_manager():
    st.set_page_config(layout="wide", page_title="Monitoraggio MAC")
    
    # Inizializzazione Session State
    if 'punti' not in st.session_state: st.session_state.punti = load_mac()
    if 'anagrafica' not in st.session_state: st.session_state.anagrafica = {}
    if 'img_params' not in st.session_state:
        st.session_state.img_params = {"w": 100, "h": 100, "rot": 0, "off_x": 0, "off_y": 0}

    st.title("🌍 Monitoraggio Sensori con Overlay Dinamico")

    # ---------- SIDEBAR CONTROLLI IMMAGINE ----------
    with st.sidebar:
        st.header("🖼️ Gestione Planimetria")
        uploaded_img = st.file_uploader("Carica Immagine/CAD (PNG/JPG/SVG)", type=['png','jpg','jpeg','svg'])
        
        if uploaded_img:
            st.subheader("Trasformazione")
            col_w, col_h = st.columns(2)
            st.session_state.img_params["w"] = col_w.number_input("Larghezza (m)", 1, 5000, st.session_state.img_params["w"])
            st.session_state.img_params["h"] = col_h.number_input("Altezza (m)", 1, 5000, st.session_state.img_params["h"])
            st.session_state.img_params["rot"] = st.slider("Rotazione (°)", 0, 360, st.session_state.img_params["rot"])
            
            st.subheader("Spostamento Fine")
            st.session_state.img_params["off_y"] = st.slider("Sposta Nord/Sud", -0.005, 0.005, 0.0, format="%.5f")
            st.session_state.img_params["off_x"] = st.slider("Sposta Est/Ovest", -0.005, 0.005, 0.0, format="%.5f")
            
            opacity = st.slider("Trasparenza", 0.0, 1.0, 0.5)

    # ---------- CARICAMENTO EXCEL ----------
    with st.expander("📂 Carica Anagrafica Excel", expanded=False):
        file_input = st.file_uploader("Trascina qui l'Excel", type=['xlsx','xlsm'])
        if file_input:
            st.session_state.anagrafica = parse_excel_advanced(file_input)
            for dl, sensori in st.session_state.anagrafica.items():
                for sn, info in sensori.items():
                    if info["lat"] and info["lon"]:
                        st.session_state.punti[f"{dl}|{sn}"] = {
                            "dl": dl, "sn": sn, "lat": info["lat"], "lon": info["lon"],
                            "params": info["params"], "color": "#0066ff"
                        }
            save_mac(st.session_state.punti)
            st.success("Dati caricati!")

    # ---------- MAPPA ----------
    center = [45.4642, 9.1900]
    if st.session_state.punti:
        lats = [p["lat"] for p in st.session_state.punti.values()]
        lons = [p["lon"] for p in st.session_state.punti.values()]
        center = [sum(lats)/len(lats), sum(lons)/len(lons)]

    m = folium.Map(location=center, zoom_start=19)

    # GESTIONE OVERLAY (Immagine o SVG)
    if uploaded_img:
        # Codifica immagine
        if "svg" in uploaded_img.name:
            svg_str = uploaded_img.read().decode()
            data_url = "data:image/svg+xml;base64," + base64.b64encode(svg_str.encode()).decode()
        else:
            img = Image.open(uploaded_img)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        # Calcolo posizione basata su parametri sidebar
        ov_lat = center[0] + st.session_state.img_params["off_y"]
        ov_lon = center[1] + st.session_state.img_params["off_x"]
        
        corners = get_rotated_corners(
            ov_lat, ov_lon, 
            st.session_state.img_params["w"], 
            st.session_state.img_params["h"], 
            st.session_state.img_params["rot"]
        )

        # Usiamo un metodo JS pulito per l'overlay ruotato
        img_id = "overlay_planimetria"
        overlay_js = f"""
        <script src="https://unpkg.com/leaflet-distortableimage@0.15.0/dist/leaflet.distortableimage.min.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/leaflet-distortableimage@0.15.0/dist/leaflet.distortableimage.min.css">
        <script>
            var checkMap = setInterval(function() {{
                if (window.map) {{
                    var img = new L.DistortableImageOverlay("{data_url}", {{
                        corners: [
                            L.latLng({corners[0][0]}, {corners[0][1]}),
                            L.latLng({corners[1][0]}, {corners[1][1]}),
                            L.latLng({corners[2][0]}, {corners[2][1]}),
                            L.latLng({corners[3][0]}, {corners[3][1]})
                        ],
                        opacity: {opacity},
                        editable: false
                    }}).addTo(window.map);
                    clearInterval(checkMap);
                }}
            }}, 100);
        </script>
        """
        m.get_root().html.add_child(folium.Element(overlay_js))

    # Marker Sensori
    for key, p in st.session_state.punti.items():
        folium.Marker(
            [p["lat"], p["lon"]],
            icon=DivIcon(html=f'<div style="background:{p.get("color","#0066ff")}; width:12px; height:12px; border-radius:50%; border:2px solid white;"></div>'),
            tooltip=f"{p['dl']} - {p['sn']}"
        ).add_to(m)

    st_folium(m, width="100%", height=700)

if __name__ == "__main__":
    run_map_manager()
