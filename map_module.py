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

CONFIG_FILE = "mac_positions.json"

# ----------------- UTILS -----------------
def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except:
            return {}
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
    df = pd.read_excel(
        xls, sheet_name="NAME" if "NAME" in xls.sheet_names else 0, header=None
    ).fillna("")
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
        except:
            lat, lon = None, None
        if dl not in ana: ana[dl] = {}
        if sn not in ana[dl]:
            ana[dl][sn] = {"lat": lat, "lon": lon, "params": []}
        param_full = f"{param} [{unit}]"
        if param_full not in ana[dl][sn]["params"]:
            ana[dl][sn]["params"].append(param_full)
    return ana

def img_to_data_url(img):
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"

# ----------------- MAIN -----------------
def run_map_manager():
    st.set_page_config(layout="wide", page_title="Monitoraggio MAC")
    st.title("🌍 Monitoraggio Sensori Georeferenziati con Overlay")

    # ---------- INIZIALIZZAZIONE SESSION_STATE ----------
    if 'punti' not in st.session_state or not isinstance(st.session_state.punti, dict):
        st.session_state.punti = load_mac()
    if 'anagrafica' not in st.session_state:
        st.session_state.anagrafica = {}
    if 'overlays' not in st.session_state:
        st.session_state.overlays = []

    # ---------- SETUP SOPRA MAPPA ----------
    with st.container():
        st.subheader("📂 Carica Excel / Inserimento manuale / Marker / Overlay")
        c1, c2 = st.columns([2,1])

        with c1:
            file_input = st.file_uploader("Carica file Excel", type=['xlsx','xlsm'])
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

            st.markdown("### Inserimento manuale")
            m_dl = st.text_input("Datalogger")
            m_sn = st.text_input("Sensore")
            c_lat, c_lon = st.columns(2)
            m_lat = c_lat.number_input("Lat", value=st.session_state.get("click_lat", 45.4642), format="%.6f")
            m_lon = c_lon.number_input("Lon", value=st.session_state.get("click_lon", 9.1900), format="%.6f")
            if st.button("➕ Aggiungi punto"):
                if m_dl and m_sn:
                    key = f"{m_dl}|{m_sn}"
                    st.session_state.punti[key] = {
                        "dl": m_dl, "sn": m_sn, "lat": m_lat, "lon": m_lon,
                        "params": [], "color": "#0066ff", "shape": "circle"
                    }
                    save_mac(st.session_state.punti)
                    st.experimental_rerun()

        with c2:
            st.markdown("### Marker predefiniti")
            m_color = st.color_picker("Colore predefinito", "#0066ff")
            m_shape = st.selectbox("Forma predefinita", ["circle","square","triangle"])
            st.markdown("### Overlay immagine/SVG")
            img_file = st.file_uploader("Carica immagine PNG/JPG", type=['png','jpg','jpeg'])
            svg_file = st.file_uploader("Carica SVG (o CAD convertito)", type=['svg'])
            opacity = st.slider("Trasparenza overlay", 0.0, 1.0, 0.5)

    # ---------- FILTRI ----------
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

    m = folium.Map(location=center, zoom_start=15)

    # Overlay immagine/SVG
    if img_file:
        img = Image.open(img_file)
        data_url = img_to_data_url(img)
        bounds = [[45.4635, 9.1895], [45.4650, 9.1910]]
        overlay_js = f"""
        <script src="https://unpkg.com/leaflet-distortableimage"></script>
        <script>
        var map = window.map_{id(m)};
        var overlay = new L.DistortableImageOverlay("{data_url}", {{
            corners: [
                [{bounds[0][0]}, {bounds[0][1]}],
                [{bounds[0][0]}, {bounds[1][1]}],
                [{bounds[1][0]}, {bounds[1][1]}],
                [{bounds[1][0]}, {bounds[0][1]}]
            ],
            opacity: {opacity}, selected:true
        }}).addTo(map);
        </script>
        """
        m.get_root().html.add_child(folium.Element(overlay_js))

    if svg_file:
        svg_data = svg_file.read().decode()
        data_url = "data:image/svg+xml;base64," + base64.b64encode(svg_data.encode()).decode()
        bounds = [[45.4635, 9.1895], [45.4650, 9.1910]]
        overlay_js = f"""
        <script src="https://unpkg.com/leaflet-distortableimage"></script>
        <script>
        var map = window.map_{id(m)};
        var overlay = new L.DistortableImageOverlay("{data_url}", {{
            corners: [
                [{bounds[0][0]}, {bounds[0][1]}],
                [{bounds[0][0]}, {bounds[1][1]}],
                [{bounds[1][0]}, {bounds[1][1]}],
                [{bounds[1][0]}, {bounds[0][1]}]
            ],
            opacity: {opacity}, selected:true
        }}).addTo(map);
        </script>
        """
        m.get_root().html.add_child(folium.Element(overlay_js))

    # Marker dinamici
    for key, p in st.session_state.punti.items():
        d_p, s_p = p["dl"], p["sn"]
        if sel_dl and sel_dl != "Tutti" and d_p != sel_dl: continue
        if sel_sn and sel_sn != "Tutti" and s_p != sel_sn: continue
        color = p.get("color", m_color)
        shape = p.get("shape", m_shape)
        rot = "transform: rotate(45deg);" if shape=="triangle" else ""
        rad = "50%" if shape=="circle" else "0%"
        popup_content = f"""
        <b>{d_p} - {s_p}</b><br>
        <b>Parametri:</b><br>{"<br>".join([par for par in p.get("params",[]) if not sel_params or par in sel_params])}<br>
        Lat: {p['lat']}<br>Lon: {p['lon']}<br>Colore: {color}<br>Forma: {shape}<br>
        """
        folium.Marker(
            [p["lat"], p["lon"]],
            icon=DivIcon(icon_size=(40,40), icon_anchor=(20,20),
                         html=f"<div style='background-color:{color}; border:2px solid white; border-radius:{rad}; width:40px; height:40px; display:flex; align-items:center; justify-content:center; color:white; font-size:9px; font-weight:bold; {rot}'>{s_p[:5]}</div>"),
            tooltip=f"{d_p} - {s_p}",
            popup=folium.Popup(popup_content, max_width=250),
            draggable=True
        ).add_to(m)

    map_res = st_folium(m, width="100%", height=600)

    if map_res and map_res.get("last_clicked"):
        st.session_state.click_lat = map_res["last_clicked"]["lat"]
        st.session_state.click_lon = map_res["last_clicked"]["lng"]

    if st.button("🗑️ Reset totale"):
        st.session_state.punti = {}
        st.session_state.anagrafica = {}
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
        st.experimental_rerun()


if __name__ == "__main__":
    run_map_manager()
