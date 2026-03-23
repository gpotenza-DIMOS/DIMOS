import streamlit as st
import pandas as pd
import json
import os
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
import re
from PIL import Image
import base64
import io

CONFIG_FILE = "mac_positions.json"

# ----------------- UTILS (RIPRISTINATE) -----------------
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

def img_to_data_url(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"

# ----------------- MAIN -----------------
def run_map_manager():
    st.set_page_config(layout="wide", page_title="Monitoraggio MAC")
    st.title("🌍 Monitoraggio Sensori Georeferenziati con Overlay")

    # ---------- SESSION STATE (RIPRISTINATO) ----------
    if 'punti' not in st.session_state or not isinstance(st.session_state.punti, dict):
        st.session_state.punti = load_mac()
    if 'anagrafica' not in st.session_state:
        st.session_state.anagrafica = {}
    if 'overlay' not in st.session_state:
        st.session_state.overlay = {"img_file": None, "corners": None, "locked": False, "opacity": 0.5}

    # ---------- BARRA SUPERIORE (RIPRISTINATA) ----------
    with st.expander("📂 Carica / Inserimento / Overlay", expanded=True):
        c1, c2, c3 = st.columns([2,1,1])
        with c1:
            file_input = st.file_uploader("Carica Excel", type=['xlsx','xlsm'], key="excel")
            if file_input:
                ana = parse_excel_advanced(file_input)
                st.session_state.anagrafica = ana
                for dl, sensori in ana.items():
                    for sn, info in sensori.items():
                        key = f"{dl}|{sn}"
                        if info["lat"] is not None and info["lon"] is not None:
                            st.session_state.punti[key] = {
                                "dl": dl, "sn": sn, "lat": info["lat"], "lon": info["lon"],
                                "params": info["params"], "color": "#0066ff", "shape": "circle"
                            }
                save_mac(st.session_state.punti)
                st.success("Excel caricato!")

            m_dl = st.text_input("Datalogger", key="manual_dl")
            m_sn = st.text_input("Sensore", key="manual_sn")
            m_lat = st.number_input("Lat", value=st.session_state.get("click_lat", 45.4642), format="%.6f", key="manual_lat")
            m_lon = st.number_input("Lon", value=st.session_state.get("click_lon", 9.1900), format="%.6f", key="manual_lon")
            if st.button("➕ Aggiungi punto"):
                if m_dl and m_sn:
                    key = f"{m_dl}|{m_sn}"
                    st.session_state.punti[key] = {
                        "dl": m_dl, "sn": m_sn, "lat": m_lat, "lon": m_lon,
                        "params": [], "color": "#0066ff", "shape": "circle"
                    }
                    save_mac(st.session_state.punti)
                    st.rerun()

        with c2:
            m_color = st.color_picker("Colore predefinito", "#0066ff", key="color_picker")
            m_shape = st.selectbox("Forma predefinita", ["circle","square","triangle"], key="shape_picker")

        with c3:
            uploaded_img = st.file_uploader("Carica Planimetria (PNG/JPG)", type=['png','jpg','jpeg'], key="img_up")
            if uploaded_img:
                st.session_state.overlay["img_file"] = uploaded_img
            
            overlay_opacity = st.slider("Trasparenza", 0.0, 1.0, st.session_state.overlay["opacity"])
            st.session_state.overlay["opacity"] = overlay_opacity
            
            locked = st.checkbox("🔒 Blocca overlay", value=st.session_state.overlay["locked"])
            st.session_state.overlay["locked"] = locked

    # ---------- FILTRI (RIPRISTINATI) ----------
    sel_dl, sel_sn, sel_params = None, None, []
    if st.session_state.anagrafica:
        ana = st.session_state.anagrafica
        c1f, c2f, c3f = st.columns(3)
        sel_dl = c1f.selectbox("Filtra Datalogger", ["Tutti"] + sorted(ana.keys()))
        relevant_sensors = sorted(ana[sel_dl].keys()) if sel_dl != "Tutti" else sorted(set(k for d in ana.values() for k in d.keys()))
        sel_sn = c2f.selectbox("Filtra Sensore", ["Tutti"] + relevant_sensors)
        if sel_dl != "Tutti" and sel_sn != "Tutti":
            params_list = ana[sel_dl][sel_sn].get("params", [])
            sel_params = c3f.multiselect("Visualizza Parametri", params_list, default=params_list[:1])

    # ---------- MAPPA ----------
    center = [45.4642, 9.1900]
    if st.session_state.punti:
        last = list(st.session_state.punti.values())[-1]
        center = [last["lat"], last["lon"]]

    m = folium.Map(location=center, zoom_start=18)

    # Iniezione LIBRERIE NECESSARIE per far apparire l'immagine
    m.get_root().html.add_child(folium.Element("""
        <link rel="stylesheet" href="https://unpkg.com/leaflet-distortableimage@0.15.0/dist/leaflet.distortableimage.min.css">
        <script src="https://unpkg.com/leaflet-distortableimage@0.15.0/dist/leaflet.distortableimage.min.js"></script>
    """))

    # ---------- OVERLAY (IMPLEMENTATO SU TUO CODICE) ----------
    if st.session_state.overlay["img_file"]:
        img = Image.open(st.session_state.overlay["img_file"])
        data_url = img_to_data_url(img)
        
        # Se i corners non esistono, li creiamo intorno al centro
        if st.session_state.overlay["corners"] is None:
            d = 0.0005
            st.session_state.overlay["corners"] = [
                [center[0]-d, center[1]-d], [center[0]-d, center[1]+d],
                [center[0]+d, center[1]+d], [center[0]+d, center[1]-d]
            ]
        
        corners = st.session_state.overlay["corners"]
        locked_js = "true" if st.session_state.overlay["locked"] else "false"

        overlay_script = f"""
        <script>
        var checkMap = setInterval(function() {{
            if (window.map) {{
                var img_overlay = new L.DistortableImageOverlay("{data_url}", {{
                    corners: [
                        L.latLng({corners[0][0]}, {corners[0][1]}),
                        L.latLng({corners[1][0]}, {corners[1][1]}),
                        L.latLng({corners[2][0]}, {corners[2][1]}),
                        L.latLng({corners[3][0]}, {corners[3][1]})
                    ],
                    selected: true,
                    opacity: {st.session_state.overlay['opacity']},
                    editable: !{locked_js}
                }}).addTo(window.map);
                
                if (!{locked_js}) {{ img_overlay.enable(); }}
                clearInterval(checkMap);
            }}
        }}, 100);
        </script>
        """
        m.get_root().html.add_child(folium.Element(overlay_script))

    # ---------- MARKER DINAMICI (RIPRISTINATI) ----------
    for key, p in st.session_state.punti.items():
        if sel_dl and sel_dl != "Tutti" and p["dl"] != sel_dl: continue
        if sel_sn and sel_sn != "Tutti" and p["sn"] != sel_sn: continue
        
        color = p.get("color", m_color)
        shape = p.get("shape", m_shape)
        rot = "transform: rotate(45deg);" if shape=="triangle" else ""
        rad = "50%" if shape=="circle" else "0%"
        
        folium.Marker(
            [p["lat"], p["lon"]],
            icon=DivIcon(icon_size=(40,40), icon_anchor=(20,20),
                         html=f"<div style='background-color:{color}; border:2px solid white; border-radius:{rad}; width:35px; height:35px; display:flex; align-items:center; justify-content:center; color:white; font-size:9px; font-weight:bold; {rot}'>{p['sn'][:5]}</div>"),
            popup=folium.Popup(f"<b>{p['dl']}</b><br>{p['sn']}", max_width=200)
        ).add_to(m)

    # Rendering
    map_res = st_folium(m, width="100%", height=650)

    # Cattura Click
    if map_res and map_res.get("last_clicked"):
        st.session_state.click_lat = map_res["last_clicked"]["lat"]
        st.session_state.click_lon = map_res["last_clicked"]["lng"]

    # Reset (Ripristinato)
    if st.button("🗑️ Reset totale"):
        st.session_state.punti = {}
        st.session_state.anagrafica = {}
        st.session_state.overlay = {"img_file": None, "corners": None, "locked": False, "opacity": 0.5}
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
        st.rerun()

if __name__ == "__main__":
    run_map_manager()
