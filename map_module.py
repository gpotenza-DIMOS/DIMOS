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
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_mac(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_coords_from_city(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_MAC_APP'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except: return None
    return None

def run_map_manager():
    st.header("🌍 Modulo MAC - Integrazione Anagrafica Excel")

    # 1. RECUPERO DATI DALLO STATO (Condiviso col Plotter)
    # Se l'utente ha caricato il file nel plotter, usiamo quello, altrimenti chiediamo il caricamento
    punti_salvati = load_mac()
    anagrafica_excel = {}
    
    with st.sidebar:
        st.subheader("📂 Sorgente Dati")
        file_input = st.file_uploader("Carica Excel Monitoraggio (Foglio NAME)", type=['xlsx', 'xlsm'], key="mac_upload")
        
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_name = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                
                # Leggiamo l'anagrafica includendo Righe 4 (Lat) e 5 (Lon)
                # Nota: df_name.iloc[3] è la riga 4, df_name.iloc[4] è la riga 5
                for c_idx in range(1, df_name.shape[1]):
                    dl = str(df_name.iloc[0, c_idx]).strip()
                    sens = str(df_name.iloc[1, c_idx]).strip()
                    try:
                        lat_val = float(df_name.iloc[3, c_idx]) if df_name.iloc[3, c_idx] != "" else None
                        lon_val = float(df_name.iloc[4, c_idx]) if df_name.iloc[4, c_idx] != "" else None
                    except:
                        lat_val, lon_val = None, None
                    
                    if dl not in anagrafica_excel: anagrafica_excel[dl] = {}
                    anagrafica_excel[dl][sens] = {"lat": lat_val, "lon": lon_val}
                st.success("Anagrafica caricata con successo")

    # 2. LOGICA DI POSIZIONAMENTO
    if not anagrafica_excel:
        st.info("👋 Benvenuto. Carica il file Excel nella sidebar per vedere i sensori o cercarli.")
        return

    # Inizializzazione mappa su Ancona o sul primo sensore con coordinate
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    with st.sidebar:
        st.divider()
        st.subheader("🔍 Navigazione")
        city = st.text_input("Cerca Località")
        if st.button("Vai"):
            c = get_coords_from_city(city)
            if c: st.session_state.center = c; st.rerun()

        st.divider()
        st.subheader("📍 Selezione Sensore")
        sel_dl = st.selectbox("Seleziona Datalogger", sorted(anagrafica_excel.keys()))
        sens_list = sorted(anagrafica_excel[sel_dl].keys())
        sel_sens = st.selectbox("Seleziona Sensore", sens_list)
        
        info_sens = anagrafica_excel[sel_dl][sel_sens]
        
        if info_sens['lat'] and info_sens['lon']:
            st.warning(f"Coordinata Excel trovata: {info_sens['lat']}, {info_sens['lon']}")
            if st.button("Usa coordinate Excel"):
                # Aggiungiamo ai punti salvati se non c'è già
                if not any(p['nome'] == sel_sens for p in punti_salvati):
                    punti_salvati.append({"nome": sel_sens, "lat": info_sens['lat'], "lon": info_sens['lon']})
                    save_mac(punti_salvati)
                    st.rerun()
        else:
            st.info("Coordinate mancanti nell'Excel. Clicca sulla mappa per piazzarlo.")

    # 3. CREAZIONE MAPPA
    m = folium.Map(location=st.session_state.center, zoom_start=15)
    
    for p in punti_salvati:
        folium.Marker([p['lat'], p['lon']], popup=p['nome'], tooltip=p['nome'],
                      icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

    st.write(f"👉 **Azione:** Clicca per posizionare il sensore selezionato: **{sel_sens}**")
    output = st_folium(m, width=1000, height=600, key="mac_map_integrated")

    # 4. SALVATAGGIO AL CLICK
    if output.get("last_clicked"):
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        # Sovrascriviamo o aggiungiamo la posizione per il sensore selezionato
        # Rimuoviamo vecchia posizione se esiste
        punti_salvati = [p for p in punti_salvati if p['nome'] != sel_sens]
        punti_salvati.append({"nome": sel_sens, "lat": lat_c, "lon": lon_c})
        save_mac(punti_salvati)
        st.rerun()

    if punti_salvati:
        with st.expander("📄 Riepilogo Posizioni"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
            if st.button("🗑️ Reset Totale"):
                save_mac([]); st.rerun()
