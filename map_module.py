import streamlit as st
import pandas as pd
import json
import os
import requests
from streamlit_folium import st_folium
import folium

CONFIG_FILE = "mac_positions.json"

# --- FUNZIONI DI SERVIZIO ---
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
        headers = {'User-Agent': 'DIMOS_MAC_FINAL'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except: return None
    return None

# --- MODULO PRINCIPALE ---
def run_map_manager():
    st.header("🌍 Dashboard MAC - Controllo Totale")

    # 1. RECUPERO ANAGRAFICA (Persistente tra i moduli)
    if 'anagrafica' not in st.session_state:
        st.warning("⚠️ Nessun dato caricato. Usa la sidebar per caricare l'Excel.")
        file_input = st.sidebar.file_uploader("📂 Carica Excel Anagrafica", type=['xlsx', 'xlsm'])
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                ana = {}
                for c in range(1, df_n.shape[1]):
                    dl = str(df_n.iloc[0, c]).strip()
                    sn = str(df_n.iloc[1, c]).strip()
                    try:
                        # Righe 4 e 5 (index 3 e 4)
                        la = float(df_n.iloc[3, c]) if df_n.iloc[3, c] != "" else None
                        lo = float(df_n.iloc[4, c]) if df_n.iloc[4, c] != "" else None
                    except: la, lo = None, None
                    
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sn] = {"lat": la, "lon": lo}
                st.session_state['anagrafica'] = ana
                st.rerun()
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()
    
    # 2. SIDEBAR DI FILTRO E RICERCA
    with st.sidebar:
        st.subheader("🔍 Navigazione")
        city_search = st.text_input("Vai a città/indirizzo")
        if st.button("Sposta Mappa"):
            coords = get_coords(city_search)
            if coords: 
                st.session_state.center = coords
                st.rerun()

        st.divider()
        st.subheader("🛠️ Gestione Sensori")
        sel_dls = st.multiselect("Visualizza Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
        
        # Filtriamo la lista sensori basandoci sui DL scelti
        opzioni_sensori = []
        for d in sel_dls:
            for s in ana[d].keys():
                opzioni_sensori.append(f"{d} | {s}")
        
        target_selection = st.selectbox("🎯 Seleziona per posizionare:", opzioni_sensori)
        
        if st.button("📌 Importa TUTTE le coordinate da Excel"):
            nuovi = []
            for d in ana:
                for s, c in ana[d].items():
                    if c['lat'] and c['lon']:
                        nuovi.append({"nome": s, "lat": c['lat'], "lon": c['lon'], "dl": d})
            save_mac(nuovi)
            st.rerun()

    # 3. CONFIGURAZIONE MAPPA (Tutti i sensori insieme)
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    m = folium.Map(location=st.session_state.center, zoom_start=15)
    
    # Disegniamo TUTTI i sensori salvati
    for p in punti_salvati:
        # Se il sensore è quello selezionato in sidebar, lo facciamo blu, gli altri rossi
        is_selected = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=f"DL: {p.get('dl','?')}<br>SN: {p['nome']}", 
            tooltip=p['nome'],
            icon=folium.Icon(color='blue' if is_selected else 'red', icon='info-sign')
        ).add_to(m)

    st.info(f"Mappa attiva con {len(punti_salvati)} sensori. Clicca per riposizionare **{target_selection}**")
    
    # Render Mappa
    output = st_folium(m, width=1100, height=650, key="mac_main_dashboard")

    # 4. SALVATAGGIO AL CLICK
    if output.get("last_clicked"):
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        dl_puro, nome_puro = target_selection.split(" | ")
        
        # Aggiorniamo la lista: togliamo il vecchio se esiste, mettiamo il nuovo
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(punti_salvati)
        st.rerun()

    # 5. TABELLA COORDINATE (In fondo)
    if punti_salvati:
        with st.expander("📄 DataBase Coordinate"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
            if st.button("🗑️ Reset Mappa"): save_mac([]); st.rerun()
