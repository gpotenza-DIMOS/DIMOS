import streamlit as st
import pandas as pd
import json
import os
import requests
import base64
from streamlit_folium import st_folium
import folium
from folium.plugins import ImageOverlay
from PIL import Image
from io import BytesIO

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

# --- MODULO PRINCIPALE ---
def run_map_manager():
    st.header("🌍 Dashboard MAC - Gestione Mappa")

    # 1. CARICAMENTO EXCEL (Sempre accessibile)
    with st.expander("📂 Carica o Cambia File Excel (Foglio NAME)", expanded=True):
        file_input = st.file_uploader("Trascina qui il file Excel", type=['xlsx', 'xlsm'], key="map_excel_loader")
        if file_input:
            try:
                xls = pd.ExcelFile(file_input)
                if "NAME" in xls.sheet_names:
                    df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                    ana = {}
                    for c in range(1, df_n.shape[1]):
                        dl = str(df_n.iloc[0, c]).strip()
                        sn = str(df_n.iloc[1, c]).strip()
                        try:
                            la = float(df_n.iloc[3, c]); lo = float(df_n.iloc[4, c])
                        except: la, lo = None, None
                        if dl not in ana: ana[dl] = {}
                        ana[dl][sn] = {"lat": la, "lon": lo}
                    st.session_state['anagrafica'] = ana
                    st.success("✅ File caricato con successo!")
            except Exception as e:
                st.error(f"Errore nella lettura del file: {e}")

    # Controllo se ci sono dati, altrimenti mi fermo qui senza dare errori
    if 'anagrafica' not in st.session_state:
        st.info("Inizia caricando un file Excel sopra.")
        return

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # --- 2. CONTROLLI PLANIMETRIA E SENSORI ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            sel_dls = st.multiselect("📡 Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
            opzioni = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
            target_selection = st.selectbox("🎯 Seleziona Sensore", opzioni)
        with c2:
            up_img = st.file_uploader("🖼️ Carica Planimetria", type=['png', 'jpg', 'jpeg'])
        with c3:
            sc = st.number_input("Scala Planimetria", value=0.002, format="%.5f", step=0.0001)
            rot = st.slider("Rotazione (°)", -180, 180, 0)
        with c4:
            opac = st.slider("Trasp.", 0.0, 1.0, 0.5)

    # --- 3. GESTIONE MAPPA ---
    if 'center' not in st.session_state:
        st.session_state.center = [43.6158, 13.5189]

    m = folium.Map(location=st.session_state.center, zoom_start=18)
    
    # Overlay Planimetria (Se presente)
    if up_img:
        try:
            img = Image.open(up_img).convert("RGBA")
            if rot != 0:
                img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            lat, lon = st.session_state.center
            b = [[lat - sc, lon - sc*1.5], [lat + sc, lon + sc*1.5]]
            ImageOverlay(image=f"data:image/png;base64,{img_b64}", bounds=b, opacity=opac, zindex=1).add_to(m)
        except:
            st.warning("Problema nel rendering dell'immagine.")

    # Disegno Marker
    for p in punti_salvati:
        is_sel = target_selection and p['nome'] in target_selection
        folium.Marker([p['lat'], p['lon']], tooltip=p['nome'],
                      icon=folium.Icon(color='blue' if is_sel else 'red')).add_to(m)

    # --- 4. RENDER E CLICK (FIXED) ---
    output = st_folium(m, width=1300, height=600, key="mac_v_final_stable")

    # Uso .get() per evitare il KeyError che ti bloccava
    click_data = output.get("last_clicked")
    if click_data:
        if target_selection and " | " in target_selection:
            dl_puro, nome_puro = target_selection.split(" | ")
            punti_salvati = [p for p in punti_salvati if p['nome'] != nome_puro]
            punti_salvati.append({
                "nome": nome_puro, 
                "lat": click_data["lat"], 
                "lon": click_data["lng"], 
                "dl": dl_puro
            })
            save_mac(punti_salvati)
            st.rerun()

    if punti_salvati:
        with st.expander("📄 Tabella Sensori Salvati"):
            st.dataframe(pd.DataFrame(punti_salvati), use_container_width=True)
