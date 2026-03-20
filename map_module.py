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
    st.header("🌍 Dashboard MAC - Controllo Globale Sensori")

    # --- 1. GESTIONE ANAGRAFICA CONDIVISA ---
    # Se l'anagrafica non è in session_state, permettiamo il caricamento
    if 'anagrafica' not in st.session_state:
        file_input = st.sidebar.file_uploader("📂 Carica Excel Anagrafica", type=['xlsx', 'xlsm'])
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name=\"NAME\", header=None).fillna("")
                ana = {}
                for c in range(1, df_n.shape[1]):
                    dl = str(df_n.iloc[0, c]).strip()
                    sn = str(df_n.iloc[1, c]).strip()
                    try:
                        # Riga 4 (index 3) e Riga 5 (index 4)
                        la = float(df_n.iloc[3, c]) if df_n.iloc[3, c] != "" else None
                        lo = float(df_n.iloc[4, c]) if df_n.iloc[4, c] != "" else None
                    except: la, lo = None, None
                    
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sn] = {"lat": la, "lon": lo}
                st.session_state['anagrafica'] = ana
                st.rerun()
        st.info("In attesa di anagrafica... Carica il file per vedere i sensori.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()
    
    # --- 2. SIDEBAR MULTI-GESTIONE ---
    with st.sidebar:
        st.subheader("🛠️ Gestione Sensori")
        
        # Selezione multipla Datalogger
        sel_dls = st.multiselect("Filtra per Datalogger", sorted(ana.keys()), default=sorted(ana.keys())[0])
        
        # Costruiamo lista sensori in base ai DL scelti
        lista_sensori_disp = []
        for d in sel_dls:
            for s in ana[d].keys():
                lista_sensori_disp.append(f"{d} | {s}")
        
        st.divider()
        st.subheader("📌 Posizionamento")
        modo = st.radio("Operazione:", ["Visualizza Tutto", "Posiziona Singolo"])
        
        target_sens = None
        if modo == "Posiziona Singolo":
            target_sens = st.selectbox("Seleziona sensore da muovere:", lista_sensori_disp)
        
        if st.button("🚀 Importa Coordinate da Excel (Tutti)"):
            nuovi_punti = []
            for d in ana:
                for s, coords in ana[d].items():
                    if coords['lat'] and coords['lon']:
                        nuovi_punti.append({"nome": s, "lat": coords['lat'], "lon": coords['lon'], "dl": d})
            save_mac(nuovi_punti)
            st.rerun()

    # --- 3. LOGICA MAPPA ---
    # Centro dinamico
    center = [43.6158, 13.5189]
    if punti_salvati:
        center = [punti_salvati[-1]['lat'], punti_salvati[-1]['lon']]

    m = folium.Map(location=center, zoom_start=15)
    
    # Visualizziamo TUTTI i sensori salvati
    for p in punti_salvati:
        # Colore diverso se è il sensore che stiamo posizionando
        color = 'blue' if target_sens and p['nome'] in target_sens else 'red'
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=f"DL: {p.get('dl','?')}<br>SN: {p['nome']}", 
            tooltip=p['nome'],
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)

    st.write(f"📊 **Mappa Attiva:** {len(punti_salvati)} sensori posizionati.")
    if modo == "Posiziona Singolo":
        st.warning(f"👉 Clicca sulla mappa per definire la posizione di: **{target_sens}**")
    
    output = st_folium(m, width=1100, height=600, key="mac_dashboard_map")

    # --- 4. SALVATAGGIO AL CLICK (Solo se in modalità posizionamento) ---
    if output.get("last_clicked") and modo == "Posiziona Singolo":
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        nome_puro = target_sens.split(" | ")[1]
        dl_puro = target_sens.split(" | ")[0]
        
        # Aggiorniamo la lista salvata
        nuova_lista = [p for p in punti_salvati if p['nome'] != nome_puro]
        nuova_lista.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(nuova_lista)
        st.rerun()

    # --- 5. TABELLA RIASSUNTIVA ---
    if punti_salvati:
        with st.expander("📄 DataBase Coordinate Attuale"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
