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
        headers = {'User-Agent': 'DIMOS_MAC_DASHBOARD'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except: return None
    return None

# --- MODULO PRINCIPALE ---
def run_map_manager():
    st.header("🌍 Dashboard MAC - Controllo Integrato")

    # 1. RECUPERO DATI DALLA SESSIONE
    if 'anagrafica' not in st.session_state:
        st.warning("⚠️ Nessun dato caricato. Carica l'Excel per attivare la mappa.")
        file_input = st.file_uploader("📂 Carica Excel Monitoraggio (Foglio NAME)", type=['xlsx', 'xlsm'])
        if file_input:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                ana = {}
                for c in range(1, df_n.shape[1]):
                    dl = str(df_n.iloc[0, c]).strip()
                    sn = str(df_n.iloc[1, c]).strip()
                    try:
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

    # --- 2. PANNELLO DI CONTROLLO PARAMETRICO (Sopra la mappa) ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        
        with c1:
            sel_dls = st.multiselect("📡 Filtra Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
        
        with c2:
            # Creiamo la lista sensori filtrata
            opzioni_sensori = []
            for d in sel_dls:
                for s in ana[d].keys():
                    opzioni_sensori.append(f"{d} | {s}")
            target_selection = st.selectbox("🎯 Seleziona Sensore da Posizionare", opzioni_sensori)
        
        with c3:
            st.write("") # Spaziatore
            if st.button("📥 Importa da Excel", use_container_width=True):
                nuovi = []
                for d in ana:
                    for s, c in ana[d].items():
                        if c['lat'] and c['lon']:
                            nuovi.append({"nome": s, "lat": c['lat'], "lon": c['lon'], "dl": d})
                save_mac(nuovi)
                st.rerun()

    # --- 3. GESTIONE MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    # Ricerca località rapida (opzionale, messa sopra la mappa)
    search_col, _ = st.columns([1, 2])
    with search_col:
        city_q = st.text_input("🔍 Cerca Città sulla Mappa", key="city_q")
        if city_q:
            coords = get_coords(city_q)
            if coords: 
                st.session_state.center = coords
                # Nota: non facciamo rerun qui per non perdere il focus
    
    m = folium.Map(location=st.session_state.center, zoom_start=15)
    
    # Visualizza tutti i sensori
    for p in punti_salvati:
        # Colore differenziato per il sensore selezionato
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=f"DL: {p.get('dl','?')}<br>SN: {p['nome']}", 
            tooltip=p['nome'],
            icon=folium.Icon(color='blue' if is_sel else 'red', icon='info-sign')
        ).add_to(m)

    # Render mappa
    output = st_folium(m, width=1300, height=600, key="mac_main_dashboard")

    # --- 4. SALVATAGGIO AL CLICK ---
    if output.get("last_clicked"):
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        dl_puro, nome_puro = target_selection.split(" | ")
        
        # Aggiornamento database
        punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
        punti_salvati.append({"nome": nome_puro, "lat": lat_c, "lon": lon_c, "dl": dl_puro})
        save_mac(punti_salvati)
        st.rerun()

    # --- 5. FOOTER DATI ---
    if punti_salvati:
        with st.expander("📄 Visualizza Tabella Coordinate"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
            if st.button("🗑️ Reset Mappa"): save_mac([]); st.rerun()
