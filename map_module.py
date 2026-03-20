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

def run_map_manager():
    st.header("🌍 Modulo MAC - Integrazione Totale")

    # 1. RECUPERO ANAGRAFICA DALLA SESSIONE (Senza reset tra moduli)
    # Se il plotter ha già caricato i dati, li usiamo. Altrimenti carichiamo qui.
    if 'anagrafica' not in st.session_state:
        st.info("💡 Carica il file Excel qui o nel modulo Plotter per iniziare.")
        file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'])
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_name = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                ana = {}
                # Estrazione come nel plotter + Righe 4 e 5 per coordinate
                for c in range(1, df_name.shape[1]):
                    dl = str(df_name.iloc[0, c]).strip()
                    sens = str(df_name.iloc[1, c]).strip()
                    try:
                        # Riga 4 (index 3) e Riga 5 (index 4)
                        lat_val = float(df_name.iloc[3, c]) if df_name.iloc[3, c] != "" else None
                        lon_val = float(df_name.iloc[4, c]) if df_name.iloc[4, c] != "" else None
                    except: lat_val, lon_val = None, None
                    
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sens] = {"lat": lat_val, "lon": lon_val}
                st.session_state['anagrafica'] = ana
                st.rerun()
        return

    # Se arriviamo qui, l'anagrafica esiste nello stato della sessione
    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # 2. SIDEBAR DI SELEZIONE (Stile Plotter)
    with st.sidebar:
        st.subheader("🛰️ Selezione Sensore")
        sel_dl = st.selectbox("Datalogger", sorted(ana.keys()))
        sel_sens = st.selectbox("Sensore", sorted(ana[sel_dl].keys()))
        
        info = ana[sel_dl][sel_sens]
        
        # Se l'Excel ha le coordinate, diamo la priorità
        if info['lat'] and info['lon']:
            st.success(f"Coordinate Excel: {info['lat']}, {info['lon']}")
            if st.button("📍 Importa da Excel"):
                # Aggiorna o aggiungi
                punti_salvati = [p for p in punti_salvati if p['nome'] != sel_sens]
                punti_salvati.append({"nome": sel_sens, "lat": info['lat'], "lon": info['lon']})
                save_mac(punti_salvati)
                st.rerun()
        
        st.divider()
        if st.button("🗑️ Svuota Mappa"):
            save_mac([])
            st.rerun()

    # 3. GESTIONE MAPPA
    # Centriamo sulla media dei punti o su Ancona
    center = [43.6158, 13.5189]
    if punti_salvati:
        center = [punti_salvati[-1]['lat'], punti_salvati[-1]['lon']]

    m = folium.Map(location=center, zoom_start=15)
    
    for p in punti_salvati:
        folium.Marker([p['lat'], p['lon']], popup=p['nome'], tooltip=p['nome'],
                      icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

    st.write(f"👉 Clicca sulla mappa per posizionare manualmente: **{sel_sens}**")
    output = st_folium(m, width=1100, height=600, key="mac_integrated_map")

    # 4. SALVATAGGIO AL CLICK
    if output.get("last_clicked"):
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        # Verifichiamo se è un nuovo click (evita loop)
        if not punti_salvati or (punti_salvati[-1]['lat'] != lat_c):
            punti_salvati = [p for p in punti_salvati if p['nome'] != sel_sens]
            punti_salvati.append({"nome": sel_sens, "lat": lat_c, "lon": lon_c})
            save_mac(punti_salvati)
            st.rerun()

    if punti_salvati:
        with st.expander("📄 DataBase Coordinate"):
            st.table(pd.DataFrame(punti_salvati))
