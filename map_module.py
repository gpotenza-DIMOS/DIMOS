import streamlit as st
import pandas as pd
import json
import os
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
import re

CONFIG_FILE = "mac_positions.json"

# ----------------- UTILS -----------------
def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    return {}
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

    if not dl:
        dl = "UNKNOWN_DL"
    if not sn:
        sn = "UNKNOWN_SENSOR"

    return dl, sn, param, unit

def parse_excel_advanced(file):
    xls = pd.ExcelFile(file)

    if "NAME" in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
    else:
        df = pd.read_excel(xls, sheet_name=0, header=None).fillna("")

    ana = {}

    for c in range(1, df.shape[1]):

        dl_raw = str(df.iloc[0, c]).strip()
        sn_raw = str(df.iloc[1, c]).strip()
        web_name = str(df.iloc[2, c]).strip()

        dl_web, sn_web, param, unit = parse_web_name(web_name)

        dl = dl_raw if dl_raw else dl_web
        sn = sn_raw if sn_raw else sn_web

        if not dl:
            dl = "UNKNOWN_DL"
        if not sn:
            sn = "UNKNOWN_SENSOR"

        try:
            lat = float(df.iloc[3, c]) if df.iloc[3, c] != "" else None
            lon = float(df.iloc[4, c]) if df.iloc[4, c] != "" else None
        except:
            lat, lon = None, None

        if dl not in ana:
            ana[dl] = {}

        if sn not in ana[dl]:
            ana[dl][sn] = {
                "lat": lat,
                "lon": lon,
                "params": []
            }

        param_full = f"{param} [{unit}]"

        if param_full not in ana[dl][sn]["params"]:
            ana[dl][sn]["params"].append(param_full)

        if lat is not None and lon is not None:
            ana[dl][sn]["lat"] = lat
            ana[dl][sn]["lon"] = lon

    return ana


# ----------------- MAIN -----------------
def run_map_manager():
    st.set_page_config(layout="wide")
    st.title("🌍 Monitoraggio Sensori Georeferenziati")

    if 'punti' not in st.session_state:
        st.session_state.punti = load_mac()

    if not isinstance(st.session_state.punti, dict):
       st.session_state.punti = {}

    if 'anagrafica' not in st.session_state:
        st.session_state.anagrafica = {}

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.header("📂 Excel")
        file_input = st.file_uploader("Carica file", type=['xlsx', 'xlsm'])

        if file_input:
            ana = parse_excel_advanced(file_input)
            st.session_state.anagrafica = ana

            for dl, sensori in ana.items():
                for sn, info in sensori.items():
                    key = f"{dl}|{sn}"

                    if info["lat"] is not None:
                        st.session_state.punti[key] = {
                            "dl": dl,
                            "sn": sn,
                            "lat": info["lat"],
                            "lon": info["lon"],
                            "params": info["params"]
                        }

            save_mac(st.session_state.punti)
            st.success("Excel caricato correttamente")

        st.divider()

        st.header("📍 Inserimento manuale")
        m_dl = st.text_input("Datalogger")
        m_sn = st.text_input("Sensore")

        col1, col2 = st.columns(2)
        m_lat = col1.number_input("Lat", value=st.session_state.get("click_lat", 45.4642))
        m_lon = col2.number_input("Lon", value=st.session_state.get("click_lon", 9.1900))

        if st.button("➕ Aggiungi punto"):
            if m_dl and m_sn:
                key = f"{m_dl}|{m_sn}"
                st.session_state.punti[key] = {
                    "dl": m_dl,
                    "sn": m_sn,
                    "lat": m_lat,
                    "lon": m_lon,
                    "params": []
                }
                save_mac(st.session_state.punti)
                st.rerun()

        st.divider()

        st.header("🎨 Marker")
        m_color = st.color_picker("Colore", "#0066ff")
        m_shape = st.selectbox("Forma", ["circle", "square", "triangle"])

    # ---------- FILTRI ROBUSTI ----------
    sel_dl = None
    sel_sn = None
    sel_params = []

    if st.session_state.anagrafica:
        ana = st.session_state.anagrafica

        c1, c2, c3 = st.columns(3)

        dl_list = sorted(ana.keys())
        sel_dl = c1.selectbox("Datalogger", dl_list)

        if sel_dl not in ana:
            st.stop()

        sn_list = sorted(ana[sel_dl].keys())

        if "sel_sn" not in st.session_state or st.session_state.sel_sn not in sn_list:
            st.session_state.sel_sn = sn_list[0]

        sel_sn = c2.selectbox("Sensore", sn_list, key="sel_sn")

        if sel_sn not in ana[sel_dl]:
            st.stop()

        params_list = ana[sel_dl][sel_sn].get("params", [])

        if params_list:
            sel_params = c3.multiselect(
                "Parametri",
                params_list,
                default=params_list[:1]
            )

    # ---------- MAPPA ----------
    center = [45.4642, 9.1900]

    if st.session_state.punti:
        last = list(st.session_state.punti.values())[-1]
        center = [last["lat"], last["lon"]]

    m = folium.Map(location=center, zoom_start=15)

    rotation = "transform: rotate(45deg);" if m_shape == "triangle" else ""
    border_rad = "50%" if m_shape == "circle" else "0%"

    for key, p in (st.session_state.punti or {}).items():

        dl = p["dl"]
        sn = p["sn"]

        if sel_dl and dl != sel_dl:
            continue
        if sel_sn and sn != sel_sn:
            continue
       for key, p in (st.session_state.punti or {}).items():

       if not isinstance(p, dict):
            continue

       if "lat" not in p or "lon" not in p:
            continue

    dl = p.get("dl", "ND")
    sn = p.get("sn", "ND")

        params = p.get("params", [])

        popup_txt = f"<b>{dl} - {sn}</b><br>"

        for par in params:
            if not sel_params or par in sel_params:
                popup_txt += f"{par}<br>"

        html_icon = f"""
        <div style="
            background-color:{m_color};
            border:2px solid white;
            border-radius:{border_rad};
            width:40px;
            height:40px;
            display:flex;
            align-items:center;
            justify-content:center;
            color:white;
            font-size:8px;
            font-weight:bold;
            text-align:center;
            {rotation}
        ">{sn}</div>
        """

        folium.Marker(
            [p["lat"], p["lon"]],
            icon=DivIcon(html=html_icon),
            tooltip=f"{dl} - {sn}",
            popup=popup_txt
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=600)

    # CLICK MAPPA
    if map_data and map_data.get("last_clicked"):
        st.session_state.click_lat = map_data["last_clicked"]["lat"]
        st.session_state.click_lon = map_data["last_clicked"]["lng"]
        st.info(f"📍 Coordinate selezionate: {st.session_state.click_lat}, {st.session_state.click_lon}")

    # RESET
    if st.button("🗑️ Reset totale"):
        st.session_state.punti = {}
        save_mac({})
        st.rerun()


if __name__ == "__main__":
    run_map_manager()
