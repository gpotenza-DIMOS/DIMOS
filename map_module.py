import streamlit as st
import pandas as pd
import json
import os
import requests
from streamlit_folium import st_folium
import folium

# File dove salviamo i tuoi sensori
CONFIG_FILE = "mac_positions.json"

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
        headers = {'User-Agent': 'DIMOS_MAC_APP'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except: return None
    return None

def run_map_manager():
    st.header("🌍 Modulo MAC (Mappa Ambiente Coordinate)")

    # Inizializzazione posizione mappa
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189] # Default: Ancona

    # Carichiamo i sensori già salvati
    punti_salvati = load_mac()

    with st.sidebar:
        st.subheader("🔍 Navigazione")
        city = st.text_input("Cerca Località", placeholder="es. Ancona")
        if st.button("Vai"):
            coords = get_coords(city)
            if coords:
                st.session_state.center = coords
                st.rerun()
        
        st.divider()
        st.subheader("📌 Inserimento")
        nome_s = st.text_input("Nome del Sensore", value=f"SENS_{len(punti_salvati)+1}")
        st.info("Scegli il nome, poi clicca sulla mappa nel punto esatto.")
        
        if st.button("🗑️ Svuota Mappa"):
            save_mac([])
            st.rerun()

    # --- COSTRUZIONE MAPPA ---
    m = folium.Map(location=st.session_state.center, zoom_start=15)
    
    # Visualizziamo i sensori che hai già caricato
    for p in punti_salvati:
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=p['nome'], 
            tooltip=p['nome'],
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

    # Mostra la mappa e cattura l'input del mouse
    st.write(f"Stai posizionando: **{nome_s}**")
    output = st_folium(m, width=1000, height=600, key="mac_map_folium")

    # --- LOGICA DI CARICAMENTO AL CLICK ---
    if output.get("last_clicked"):
        lat_click = output["last_clicked"]["lat"]
        lon_click = output["last_clicked"]["lng"]
        
        # Controlliamo che non stiamo salvando lo stesso punto due volte
        if not punti_salvati or (punti_salvati[-1]['lat'] != lat_click):
            nuovo_sensore = {
                "nome": nome_s,
                "lat": lat_click,
                "lon": lon_click
            }
            punti_salvati.append(nuovo_sensore)
            save_mac(punti_salvati)
            st.success(f"✅ Sensore '{nome_s}' caricato sulla mappa!")
            st.rerun()

    # Tabella dati sotto la mappa
    if punti_salvati:
        with st.expander("📄 Tabella Coordinate Sensori"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
