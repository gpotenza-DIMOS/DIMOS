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
from io import BytesIO

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
    """Logica per estrarre info dal nome web se manca il layer NAME"""
    unit = re.findall(r'\[(.*?)\]', web_name)
    unit = unit[0] if unit else ""
    clean_name = re.sub(r'\[.*?\]', '', web_name).strip()
    parts = clean_name.split()
    dl = parts[0] if len(parts) > 0 else "DL_SCONOSCIUTO"
    full_sensor = parts[1] if len(parts) > 1 else "SN_SCONOSCIUTO"
    
    # Gestione parametri (es. CL_01_X)
    sensor_parts = full_sensor.split('_')
    if len(sensor_parts) > 2:
        sn = "_".join(sensor_parts[:-1])
        param = sensor_parts[-1]
    else:
        sn = full_sensor
        param = "Dato"
    return dl, sn, param, unit

def parse_excel_completo(file):
    xls = pd.ExcelFile(file)
    if "NAME" in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
    else:
        df = pd.read_excel(xls, sheet_name=0, header=None).fillna("")

    ana = {}
    # Partiamo dalla colonna 1 (B)
    for c in range(1, df.shape[1]):
        dl_row1 = str(df.iloc[0, c]).strip()
        sn_row2 = str(df.iloc[1, c]).strip()
        web_name = str(df.iloc[2, c]).strip()
        
        # Se i nomi in riga 1 e 2 mancano, decodifichiamo il nome web (riga 3)
        dl_web, sn_web, param, unit = parse_web_name(web_name)
        
        dl = dl_row1 if dl_row1 else dl_web
        sn = sn_row2 if sn_row2 else sn_web
        
        # Coordinate (Righe 4 e 5)
        try:
            lat = float(df.iloc[3, c]) if df.iloc[3, c] != "" else None
            lon = float(df.iloc[4, c]) if df.iloc[4, c] != "" else None
        except: lat, lon = None, None

        if dl not in ana: ana[dl] = {}
        if sn not in ana[dl]:
            ana[dl][sn] = {"lat": lat, "lon": lon, "params": []}
        
        # Aggiungiamo il parametro specifico (X, Y, T1...)
        param_label = f"{param} [{unit}]" if unit else param
        if param_label not in ana[dl][sn]["params"]:
            ana[dl][sn]["params"].append(param_label)
            
    return ana

# ----------------- MAIN -----------------
def run_map_manager():
    st.set_page_config(layout="wide", page_title="Monitoraggio Avanzato DIMOS")
    st.title("🌍 Dashboard Monitoraggio Sensori (Versione Completa)")

    if 'punti' not in st.session_state:
        st.session_state.punti = load_mac()
    if 'anagrafica' not in st.session_state:
        st.session_state.anagrafica = {}

    # ---------- SIDEBAR GESTIONE ----------
    with st.sidebar:
        st.header("📂 Caricamento Dati")
        file_input = st.file_uploader("Excel (Foglio NAME)", type=['xlsx','xlsm'])
        if file_input:
            ana = parse_excel_completo(file_input)
            st.session_state.anagrafica = ana
            # Popoliamo i punti se l'Excel ha le coordinate
            for dl, sensori in ana.items():
                for sn, info in sensori.items():
                    if info["lat"] and info["lon"]:
                        key = f"{dl}|{sn}"
                        st.session_state.punti[key] = {
                            "dl": dl, "sn": sn, "lat": info["lat"], "lon": info["lon"],
                            "params": info["params"]
                        }
            save_mac(st.session_state.punti)
            st.success("Excel Elaborato")

        st.divider()
        st.header("📍 Inserimento Manuale / Click")
        m_dl = st.text_input("Nome Datalogger")
        m_sn = st.text_input("Nome Sensore")
        m_lat = st.number_input("Lat", value=st.session_state.get("click_lat", 45.4642), format="%.6f")
        m_lon = st.number_input("Lon", value=st.session_state.get("click_lon", 9.1900), format="%.6f")
        
        if st.button("➕ Registra Posizione"):
            if m_dl and m_sn:
                key = f"{m_dl}|{m_sn}"
                st.session_state.punti[key] = {
                    "dl": m_dl, "sn": m_sn, "lat": m_lat, "lon": m_lon, "params": []
                }
                save_mac(st.session_state.punti)
                st.rerun()

        st.divider()
        st.header("🖼️ Overlay Planimetria")
        img_up = st.file_uploader("Carica Immagine", type=['png','jpg','jpeg'])
        ov_scale = st.slider("Scala Overlay", 0.0001, 0.0100, 0.0020, format="%.4f")
        ov_opacity = st.slider("Trasparenza", 0.0, 1.0, 0.5)

    # ---------- FILTRI VISUALIZZAZIONE ----------
    col1, col2, col3 = st.columns(3)
    sel_dl, sel_sn, sel_params = None, None, []
    
    if st.session_state.anagrafica:
        ana = st.session_state.anagrafica
        sel_dl = col1.selectbox("📡 Seleziona Datalogger", ["Tutti"] + sorted(ana.keys()))
        
        sensors = []
        if sel_dl != "Tutti":
            sensors = sorted(ana[sel_dl].keys())
        else:
            for d in ana: sensors.extend(ana[d].keys())
            sensors = sorted(list(set(sensors)))
            
        sel_sn = col2.selectbox("🎯 Seleziona Sensore", ["Tutti"] + sensors)
        
        if sel_dl != "Tutti" and sel_sn != "Tutti":
            p_list = ana[sel_dl][sel_sn]["params"]
            sel_params = col3.multiselect("📊 Grandezze Fisiche", p_list, default=p_list[:1])

    # ---------- MAPPA ----------
    center = [45.4642, 9.1900]
    if st.session_state.punti:
        last = list(st.session_state.punti.values())[-1]
        center = [last["lat"], last["lon"]]

    m = folium.Map(location=center, zoom_start=19)

    # Overlay Immagine
    if img_up:
        img = Image.open(img_up)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        data_url = f"data:image/png;base64,{b64}"
        bounds = [[center[0]-ov_scale, center[1]-ov_scale], [center[0]+ov_scale, center[1]+ov_scale]]
        ImageOverlay(image=data_url, bounds=bounds, opacity=ov_opacity).add_to(m)

    # Marker
    for key, p in st.session_state.punti.items():
        # Applica Filtri
        if sel_dl and sel_dl != "Tutti" and p["dl"] != sel_dl: continue
        if sel_sn and sel_sn != "Tutti" and p["sn"] != sel_sn: continue

        # Stile Marker (Cerchio blu se selezionato, rosso altrimenti)
        color = "blue" if (p["dl"] == sel_dl and p["sn"] == sel_sn) else "red"
        
        # Popup con tutte le grandezze fisiche del sensore
        popup_html = f"<b>Centralina:</b> {p['dl']}<br><b>Sensore:</b> {p['sn']}<br><b>Misure:</b><br>"
        for par in p.get("params", []):
            popup_html += f"- {par}<br>"

        folium.Marker(
            [p["lat"], p["lon"]],
            icon=DivIcon(icon_size=(150,36), icon_anchor=(7,20),
                         html=f'<div style="font-size: 10pt; color: {color}; font-weight: bold;">'
                              f'<span style="background-color: white; border: 1px solid {color}; border-radius: 3px; padding: 2px;">{p["sn"]}</span>'
                              f'</div>'),
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=p["sn"]
        ).add_to(m)

    # Render Mappa e cattura click
    map_res = st_folium(m, width="100%", height=650)

    if map_res and map_res.get("last_clicked"):
        st.session_state.click_lat = map_res["last_clicked"]["lat"]
        st.session_state.click_lon = map_res["last_clicked"]["lng"]
        st.rerun()

    # Reset
    if st.button("🗑️ Reset Mappa"):
        st.session_state.punti = {}
        save_mac({})
        st.rerun()

if __name__ == "__main__":
    run_map_manager()
