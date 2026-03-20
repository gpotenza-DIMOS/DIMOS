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

# Configurazione costanti
CONFIG_FILE = "mac_positions.json"
OVERLAY_FILE = "overlay_config.json"

# --- FUNZIONI DI SUPPORTO ---
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

@st.cache_data(ttl=3600)
def get_city_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_APP_V3'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200 and r.json():
            return float(r.json()[0]['lat']), float(r.json()[0]['lon'])
    except: return None
    return None

# ------------------ LA FUNZIONE CHE IL TUO MAIN CERCA ------------------
def run_map_manager():
    st.subheader("📍 Gestione Posizionamento Sensori MAC")

    # Inizializzazione Session State robusta
    if 'punti' not in st.session_state:
        st.session_state.punti = load_json_safe(CONFIG_FILE)
    if 'center' not in st.session_state:
        st.session_state.center = [45.4642, 9.1900]

    # --- SIDEBAR PER CARICAMENTO EXCEL ---
    with st.sidebar:
        st.image("https://www.microgeo.it/wp-content/uploads/2023/04/logo-microgeo.png", width=150) # Estetica
        up = st.file_uploader("Carica Anagrafica (.xlsx)", type=['xlsx'])
        if up:
            try:
                df_ana = pd.read_excel(up, sheet_name="NAME", header=None).fillna("")
                ana_dict = {}
                for c in range(1, df_ana.shape[1]):
                    dl = str(df_ana.iloc[0, c]).strip()
                    sn = str(df_ana.iloc[1, c]).strip()
                    if dl and dl != "nan":
                        if dl not in ana_dict: ana_dict[dl] = []
                        ana_dict[dl].append(sn)
                st.session_state['anagrafica_data'] = ana_dict
                st.success("Anagrafica Caricata")
            except Exception as e:
                st.error(f"Errore foglio NAME: {e}")

    if 'anagrafica_data' not in st.session_state:
        st.info("💡 Carica il file Excel dalla sidebar per iniziare.")
        st.stop()

    # --- INTERFACCIA DI CONTROLLO ---
    ana = st.session_state['anagrafica_data']
    
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_dl = st.multiselect("📡 Datalogger", list(ana.keys()), default=list(ana.keys()))
    with c2:
        lista_full = [f"{d} | {s}" for d in sel_dl for s in ana[d]]
        visibili = st.multiselect("👁️ Mostra", lista_full, default=lista_full)
    with c3:
        target = st.selectbox("🎯 Seleziona per muovere/posizionare", lista_full)

    # --- GESTIONE MAPPA E OVERLAY ---
    search = st.text_input("🔍 Cerca località (es. Firenze)")
    if search:
        new_c = get_city_coords(search)
        if new_c: st.session_state.center = new_c

    m = folium.Map(location=st.session_state.center, zoom_start=19, control_scale=True)

    # Marker esistenti
    for p in st.session_state.punti:
        tag = f"{p['dl']} | {p['nome']}"
        if tag in visibili:
            color = 'red' if tag == target else 'blue'
            folium.Marker([p['lat'], p['lon']], popup=tag, 
                          icon=folium.Icon(color=color, icon='microchip', prefix='fa')).add_to(m)

    # Rende la mappa
    scelta = st_folium(m, width="100%", height=550, key="dimos_map")

    # Logica Click (Update)
    if scelta and scelta.get("last_clicked") and target:
        lat_c = scelta["last_clicked"]["lat"]
        lon_c = scelta["last_clicked"]["lng"]
        dl_target, sn_target = target.split(" | ")
        
        # Rimuovi vecchio se esiste e aggiungi nuovo
        st.session_state.punti = [p for p in st.session_state.punti if not (p['dl']==dl_target and p['nome']==sn_target)]
        st.session_state.punti.append({"dl": dl_target, "nome": sn_target, "lat": lat_c, "lon": lon_c})
        
        save_json_safe(CONFIG_FILE, st.session_state.punti)
        st.rerun()

    # Espositore Dati
    with st.expander("📋 Tabella Coordinate"):
        if st.session_state.punti:
            st.table(pd.DataFrame(st.session_state.punti))
            if st.button("🔴 Reset Completo Mappa"):
                save_json_safe(CONFIG_FILE, [])
                st.session_state.punti = []
                st.rerun()

# --- CALLBACK PER STREAMLIT ---
if __name__ == "__main__":
    run_map_manager()
