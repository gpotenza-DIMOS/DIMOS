import streamlit as st
import pandas as pd
import json
import os
import requests
import base64
import folium
from streamlit_folium import st_folium
from folium.raster_layers import ImageOverlay
from PIL import Image
from io import BytesIO

CONFIG_FILE = "mac_positions.json"

def load_json_safe(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except: return []
    return []

def save_json_safe(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def parse_excel_with_coords(file):
    try:
        xls = pd.ExcelFile(file)
        if "NAME" not in xls.sheet_names: return None
        df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
        
        ana = {}
        excel_points = []
        
        for c in range(1, df.shape[1]):
            dl = str(df.iloc[0, c]).strip()
            sn = str(df.iloc[1, c]).strip()
            
            if dl and dl != "nan" and dl != "":
                if dl not in ana: ana[dl] = []
                ana[dl].append(sn)
                
                # Cerca coordinate nelle righe 3 e 4 (indice 3 e 4 di pandas)
                try:
                    lat_ex = float(df.iloc[3, c])
                    lon_ex = float(df.iloc[4, c])
                    excel_points.append({"dl": dl, "nome": sn, "lat": lat_ex, "lon": lon_ex})
                except (ValueError, TypeError):
                    continue
        return ana, excel_points
    except: return None, []

def run_map_manager():
    st.subheader("📍 Gestione Posizionamento Sensori MAC")

    if 'punti' not in st.session_state:
        st.session_state.punti = load_json_safe(CONFIG_FILE)
    if 'center' not in st.session_state:
        st.session_state.center = [43.61, 13.52] # Default Ancona/Falconara come da tuo screen

    with st.sidebar:
        st.image("https://www.microgeo.it/wp-content/uploads/2023/04/logo-microgeo.png", width=150)
        up = st.file_uploader("Carica Anagrafica (.xlsx)", type=['xlsx'])
        
        if up:
            ana, ex_punti = parse_excel_with_coords(up)
            if ana:
                st.session_state['anagrafica_data'] = ana
                # Sincronizza i punti dell'Excel con quelli del JSON (l'Excel vince se presente)
                current_punti = {f"{p['dl']}|{p['nome']}": p for p in st.session_state.punti}
                for ep in ex_punti:
                    current_punti[f"{ep['dl']}|{ep['nome']}"] = ep
                
                st.session_state.punti = list(current_punti.values())
                save_json_safe(CONFIG_FILE, st.session_state.punti)
                st.success(f"Caricati {len(ex_punti)} sensori con coordinate.")

    if 'anagrafica_data' not in st.session_state:
        st.info("💡 Carica l'Excel per visualizzare i sensori e le coordinate pre-esistenti.")
        st.stop()

    ana = st.session_state['anagrafica_data']
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_dl = st.multiselect("📡 Datalogger", list(ana.keys()), default=list(ana.keys()))
    with c2:
        lista_full = [f"{d} | {s}" for d in sel_dl for s in ana[d]]
        visibili = st.multiselect("👁️ Mostra", lista_full, default=lista_full)
    with c3:
        target = st.selectbox("🎯 Target per muovere", lista_full)

    m = folium.Map(location=st.session_state.center, zoom_start=17)

    for p in st.session_state.punti:
        tag = f"{p['dl']} | {p['nome']}"
        if tag in visibili:
            is_target = (tag == target)
            folium.Marker(
                [p['lat'], p['lon']], 
                popup=tag, 
                tooltip=tag,
                icon=folium.Icon(color='red' if is_target else 'blue', icon='info-sign')
            ).add_to(m)

    scelta = st_folium(m, width=1200, height=550, key="map_v4")

    if scelta and scelta.get("last_clicked") and target:
        lat_c, lon_c = scelta["last_clicked"]["lat"], scelta["last_clicked"]["lng"]
        dl_t, sn_t = target.split(" | ")
        
        # Aggiorna posizione
        st.session_state.punti = [p for p in st.session_state.punti if not (p['dl']==dl_t and p['nome']==sn_t)]
        st.session_state.punti.append({"dl": dl_t, "nome": sn_t, "lat": lat_c, "lon": lon_c})
        
        save_json_safe(CONFIG_FILE, st.session_state.punti)
        st.rerun()

    with st.expander("📋 Tabella Coordinate Correnti"):
        if st.session_state.punti:
            st.dataframe(pd.DataFrame(st.session_state.punti), use_container_width=True)

if __name__ == "__main__":
    run_map_manager()
