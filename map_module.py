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
                return json.load(f)
        except: return {}
    return {}

def save_mac(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def parse_web_name(web_name):
    """Estrae Datalogger, Sensore, Parametro e Unità dal nome web."""
    # Esempio: CO_9277 CL_01_X [°]
    unit = re.findall(r'\[(.*?)\]', web_name)
    unit = unit[0] if unit else ""
    clean_name = re.sub(r'\[.*?\]', '', web_name).strip()
    parts = clean_name.split()
    
    dl = parts[0] if len(parts) > 0 else "Unknown"
    # Gestione multisensore (CL_01_X -> Sensore: CL_01, Parametro: X)
    full_sensor = parts[1] if len(parts) > 1 else "Unknown"
    sensor_parts = full_sensor.split('_')
    
    if len(sensor_parts) > 2: # Caso CL_01_X
        sn = "_".join(sensor_parts[:-1])
        param = sensor_parts[-1]
    else:
        sn = full_sensor
        param = "Dato"
        
    return dl, sn, param, unit

def parse_excel_advanced(file):
    xls = pd.ExcelFile(file)
    df = None
    if "NAME" in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
    else:
        # Se non c'è NAME, prendo il primo foglio disponibile
        df = pd.read_excel(xls, sheet_name=0, header=None).fillna("")
    
    ana = {}
    for c in range(1, df.shape[1]):
        # Lettura righe secondo tua specifica
        dl_raw = str(df.iloc[0, c]).strip()
        sn_raw = str(df.iloc[1, c]).strip()
        web_name = str(df.iloc[2, c]).strip()
        
        # Se NAME manca, uso parse_web_name per definire DL e SN
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
        
        ana[dl][sn]["params"].append(f"{param} [{unit}]")
        # Aggiorno coordinate se trovate
        if lat and lon:
            ana[dl][sn]["lat"] = lat
            ana[dl][sn]["lon"] = lon
            
    return ana

# ----------------- MAIN -----------------
def run_map_manager():
    st.set_page_config(layout="wide")
    st.title("🌍 Monitoraggio Sensori Georeferenziati")

    if 'punti_manuali' not in st.session_state:
        st.session_state.punti_manuali = load_mac()

    # ---------- SIDEBAR: INPUT & CONFIG ----------
    with st.sidebar:
        st.header("📂 Gestione Dati")
        file_input = st.file_uploader("Carica Excel", type=['xlsx','xlsm'])
        
        if file_input:
            ana = parse_excel_advanced(file_input)
            st.session_state['anagrafica'] = ana
            # Unisco dati Excel ai punti salvati
            for dl, sensori in ana.items():
                for sn, info in sensori.items():
                    key = f"{dl}|{sn}"
                    if info['lat'] and key not in st.session_state.punti_manuali:
                        st.session_state.punti_manuali[key] = {
                            "dl": dl, "sn": sn, "lat": info['lat'], "lon": info['lon']
                        }
            save_mac(st.session_state.punti_manuali)

        st.divider()
        st.header("📍 Inserimento Manuale")
        m_dl = st.text_input("Datalogger")
        m_sn = st.text_input("Sensore")
        col_lat, col_lon = st.columns(2)
        m_lat = col_lat.number_input("Lat", format="%.6f", value=st.session_state.get('click_lat', 0.0))
        m_lon = col_lon.number_input("Lon", format="%.6f", value=st.session_state.get('click_lon', 0.0))
        
        if st.button("Salva Punto"):
            if m_dl and m_sn:
                key = f"{m_dl}|{m_sn}"
                st.session_state.punti_manuali[key] = {"dl": m_dl, "sn": m_sn, "lat": m_lat, "lon": m_lon}
                save_mac(st.session_state.punti_manuali)
                st.rerun()

        st.divider()
        st.header("🎨 Stile Marker")
        m_color = st.color_picker("Colore", "#0000FF")
        m_shape = st.selectbox("Forma", ["circle", "square", "triangle"])

    # ---------- FILTRI MAPPA ----------
    if 'anagrafica' in st.session_state:
        ana = st.session_state['anagrafica']
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_dl = st.selectbox("📡 Datalogger", sorted(ana.keys()))
        with c2:
            sel_sn = st.selectbox("🎯 Sensore", sorted(ana[sel_dl].keys()))
        with c3:
            options = ana[sel_dl][sel_sn]["params"]
            sel_params = st.multiselect("📊 Grandezze da visualizzare", options, default=options[0])

    # ---------- MAPPA ----------
    # Centro mappa sull'ultimo punto o default
    center = [45.4642, 9.1900]
    if st.session_state.punti_manuali:
        last_p = list(st.session_state.punti_manuali.values())[-1]
        center = [last_p['lat'], last_p['lon']]

    m = folium.Map(location=center, zoom_start=15)

    # Rendering Marker
    border_rad = "50%" if m_shape == "circle" else "0%"
    
    for key, p in st.session_state.punti_manuali.items():
        # HTML per il marker personalizzato
        html_icon = f'''
        <div style="
            background-color: {m_color};
            border: 2px solid white;
            border-radius: {border_rad};
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 8px;
            font-weight: bold;
            text-align: center;
            transform: rotate(45deg) if shape=='triangle' else none;
        ">{p['sn']}</div>
        '''
        
        folium.Marker(
            [p['lat'], p['lon']],
            icon=DivIcon(icon_size=(40,40), icon_anchor=(20,20), html=html_icon),
            tooltip=f"DL: {p['dl']} - SN: {p['sn']}"
        ).add_to(m)

    # Gestione interazione
    map_data = st_folium(m, width="100%", height=600)

    # Cattura coordinate da click
    if map_data.get("last_clicked"):
        st.session_state.click_lat = map_data["last_clicked"]["lat"]
        st.session_state.click_lon = map_data["last_clicked"]["lng"]
        st.toast(f"Coordinate catturate: {st.session_state.click_lat}, {st.session_state.click_lon}")

    # Reset
    if st.button("🗑️ Reset Totale"):
        save_mac({})
        st.session_state.punti_manuali = {}
        st.rerun()

if __name__ == "__main__":
    run_map_manager()
