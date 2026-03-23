import streamlit as st
import pandas as pd
import json
import os
import folium
from folium.features import DivIcon
from folium.raster_layers import ImageOverlay # Metodo più stabile
from streamlit_folium import st_folium
import re
from PIL import Image
import base64
from io import BytesIO

CONFIG_FILE = "mac_positions.json"

# --- [FUNZIONI UTILS RIMASTE INVARIATE: load_mac, save_mac, parse_web_name, parse_excel_advanced] ---

def img_to_data_url(img):
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"

def run_map_manager():
    st.set_page_config(layout="wide", page_title="Monitoraggio MAC")
    st.title("🌍 Monitoraggio Sensori con Overlay Planimetrico")

    # Inizializzazione Session State
    if 'punti' not in st.session_state:
        st.session_state.punti = load_mac()
    if 'anagrafica' not in st.session_state:
        st.session_state.anagrafica = {}

    # --- SIDEBAR PER GESTIONE OVERLAY E INPUT ---
    with st.sidebar:
        st.header("🖼️ Planimetria (Overlay)")
        img_file = st.file_uploader("Carica Planimetria (PNG/JPG)", type=['png','jpg','jpeg'])
        opacity = st.slider("Trasparenza", 0.0, 1.0, 0.5)
        # Slider per regolare la dimensione dell'immagine sulla mappa
        img_scale = st.slider("Scala Immagine", 0.0001, 0.01, 0.002, format="%.4f")
        
        st.divider()
        st.header("📍 Nuovo Sensore")
        m_dl = st.text_input("Datalogger (es. C8A_202AS)")
        m_sn = st.text_input("Sensore (es. S_203)")
        m_lat = st.number_input("Latitudine", value=st.session_state.get("click_lat", 45.4642), format="%.6f")
        m_lon = st.number_input("Longitudine", value=st.session_state.get("click_lon", 9.1900), format="%.6f")
        
        if st.button("➕ Registra Punto"):
            if m_dl and m_sn:
                key = f"{m_dl}|{m_sn}"
                st.session_state.punti[key] = {
                    "dl": m_dl, "sn": m_sn, "lat": m_lat, "lon": m_lon,
                    "params": [], "color": "#0066ff", "shape": "circle"
                }
                save_mac(st.session_state.punti)
                st.rerun()

    # --- AREA CARICAMENTO EXCEL ---
    file_input = st.file_uploader("Carica file Excel (Anagrafica)", type=['xlsx','xlsm'])
    if file_input:
        st.session_state.anagrafica = parse_excel_advanced(file_input)
        # Unione dati... (come nel tuo codice)
        st.success("Anagrafica aggiornata")

    # --- MAPPA ---
    center = [45.4642, 9.1900]
    if st.session_state.punti:
        last = list(st.session_state.punti.values())[-1]
        center = [last["lat"], last["lon"]]

    m = folium.Map(location=center, zoom_start=18, control_scale=True)

    # Gestione Overlay Immagine (Planimetria)
    if img_file:
        img = Image.open(img_file)
        data_url = img_to_data_url(img)
        # Calcolo bounds basato sul centro e sullo scale slider
        lat_c, lon_c = center
        bounds = [[lat_c - img_scale, lon_c - img_scale], [lat_c + img_scale, lon_c + img_scale]]
        ImageOverlay(image=data_url, bounds=bounds, opacity=opacity, interactive=True, cross_origin=True).add_to(m)

    # Marker Dinamici
    for key, p in st.session_state.punti.items():
        # Filtri (DL/SN)...
        color = p.get("color", "#0066ff")
        shape = p.get("shape", "circle")
        
        # Logica visiva per multisensore (es. CL_01)
        # Se il sensore ha molti parametri, usiamo un bordo dorato
        border = "3px solid gold" if len(p.get("params", [])) > 3 else "2px solid white"
        rad = "50%" if shape == "circle" else "0%"
        
        html_icon = f"""
            <div style="background-color:{color}; border:{border}; border-radius:{rad}; 
                 width:40px; height:40px; display:flex; align-items:center; justify-content:center; 
                 color:white; font-size:9px; font-weight:bold;">{p['sn'][:5]}</div>
        """
        
        folium.Marker(
            [p["lat"], p["lon"]],
            icon=DivIcon(icon_size=(40,40), icon_anchor=(20,20), html=html_icon),
            popup=folium.Popup(f"<b>{p['dl']}</b><br>{p['sn']}<br>{'<br>'.join(p['params'])}", max_width=200)
        ).add_to(m)

    # Render Mappa
    map_res = st_folium(m, width="100%", height=600)

    # Cattura click per aggiornare i campi manuali
    if map_res and map_res.get("last_clicked"):
        st.session_state.click_lat = map_res["last_clicked"]["lat"]
        st.session_state.click_lon = map_res["last_clicked"]["lng"]
        st.rerun()

if __name__ == "__main__":
    run_map_manager()
