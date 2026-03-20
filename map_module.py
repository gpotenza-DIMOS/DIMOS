import streamlit as st
import pandas as pd
import json
import os
import requests
from streamlit_folium import st_folium
import folium

CONFIG_FILE = "mac_positions.json"

def load_mac():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    return []

def save_mac(data):
    with open(CONFIG_FILE, "w") as f: json.dump(data, f)

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_App_v1'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except:
        return None
    return None

def run_map_manager():
    st.header("🌍 Modulo MAC (Mappa Ambiente Coordinate)")

    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189] # Default Ancona

    with st.sidebar:
        st.subheader("🔍 Cerca Località")
        city = st.text_input("Inserisci Città (es. Ancona, Milano...)")
        if st.button("Vai alla posizione"):
            coords = get_coords(city)
            if coords:
                st.session_state.center = coords
                st.rerun()
            else:
                st.error("Località non trovata")

        st.divider()
        st.subheader("📌 Nuovo Sensore")
        nome_s = st.text_input("Identificativo Sensore", value="SENS_01")
        st.info("Clicca sulla mappa nel punto esatto per posizionare il sensore.")

    punti = load_mac()
    
    # Crea Mappa
    m = folium.Map(location=st.session_state.center, zoom_start=14)
    
    # Visualizza sensori salvati
    for p in punti:
        folium.Marker([p['lat'], p['lon']], popup=p['nome'], tooltip=p['nome']).add_to(m)

    # Render mappa e cattura click
    output = st_folium(m, width=900, height=600, key="mac_map")

    if output.get("last_clicked"):
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        # Salvataggio immediato al click
        nuovo = {"nome": nome_s, "lat": lat_c, "lon": lon_c}
        if not punti or (punti[-1]['lat'] != lat_c):
            punti.append(nuovo)
            save_mac(punti)
            st.success(f"Piazzato {nome_s} a {lat_c}, {lon_c}")
            st.rerun()

    if punti:
        with st.expander("📊 Riepilogo Coordinate"):
            st.dataframe(pd.DataFrame(punti))
            if st.button("🗑️ Svuota Tutto"):
                save_mac([])
                st.rerun()
