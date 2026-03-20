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

# --- COSTANTI ---
CONFIG_FILE = "mac_positions.json"
OVERLAY_FILE = "overlay_config.json"

# --- UTILS ---
def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                return data if data is not None else []
        except: return []
    return []

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

@st.cache_data(show_spinner=False)
def get_coords_cached(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_MAC_PRO'}
        res = requests.get(url, headers=headers).json()
        if res:
            return float(res[0]['lat']), float(res[0]['lon'])
    except: return None
    return None

def parse_excel(file):
    try:
        xls = pd.ExcelFile(file)
        if "NAME" not in xls.sheet_names:
            return None
        df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
        ana = {}
        for c in range(1, df.shape[1]):
            dl = str(df.iloc[0, c]).strip()
            sn = str(df.iloc[1, c]).strip()
            if not dl or dl == "nan" or dl == "": continue
            if dl not in ana: ana[dl] = {}
            ana[dl][sn] = {"lat": None, "lon": None}
        return ana
    except: return None

# ------------------ FUNZIONE PRINCIPALE (NOME CORRETTO) ------------------
def run_map_manager():
    st.title("🌍 Dashboard MAC PRO")

    # Inizializzazione Session State per evitare crash al primo avvio
    if 'punti' not in st.session_state:
        st.session_state.punti = load_json(CONFIG_FILE)
    if 'center' not in st.session_state:
        st.session_state.center = [45.4642, 9.1900]

    # ----------- SIDEBAR / GESTIONE EXCEL -----------
    with st.sidebar:
        st.header("📂 Configurazione")
        file_input = st.file_uploader("Carica Excel (Foglio NAME)", type=['xlsx','xlsm'])

        if file_input:
            ana = parse_excel(file_input)
            if ana:
                st.session_state['anagrafica'] = ana
                st.success("Anagrafica caricata")
            else:
                st.error("Errore: Foglio 'NAME' non trovato")

        if 'anagrafica' in st.session_state:
            if st.button("🔄 Reset Excel"):
                del st.session_state['anagrafica']
                st.rerun()

    if 'anagrafica' not in st.session_state:
        st.warning("Carica il file Excel per visualizzare i sensori.")
        st.stop()

    ana = st.session_state['anagrafica']

    # ----------- FILTRI E CONTROLLI -----------
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sel_dls = st.multiselect("📡 Datalogger", list(ana.keys()), default=list(ana.keys()))
    
    with col2:
        sensori_filtrati = [f"{d} | {s}" for d in sel_dls for s in ana[d]]
        sensori_visibili = st.multiselect("👁️ Sensori visibili", sensori_filtrati, default=sensori_filtrati)
    
    with col3:
        target = st.selectbox("🎯 Target per posizionamento", sensori_filtrati)

    # ----------- OVERLAY CONFIG -----------
    overlay_conf = load_json(OVERLAY_FILE)
    if isinstance(overlay_conf, list): overlay_conf = {} # Protezione da file corrotti

    with st.expander("🖼️ Overlay Planimetria"):
        img_file = st.file_uploader("Carica immagine", type=["png","jpg","jpeg"])
        scale = st.slider("Scala", 0.0001, 0.02, overlay_conf.get("scale", 0.002), format="%.4f")
        rotation = st.slider("Rotazione", -180, 180, overlay_conf.get("rotation", 0))
        opacity = st.slider("Trasparenza", 0.0, 1.0, overlay_conf.get("opacity", 0.5))
        
        if st.button("💾 Salva Overlay"):
            save_json(OVERLAY_FILE, {"scale": scale, "rotation": rotation, "opacity": opacity})
            st.success("Configurazione salvata")

    # ----------- MAPPA -----------
    city = st.text_input("🔍 Cerca città", placeholder="es. Milano")
    if city:
        coords = get_coords_cached(city)
        if coords: st.session_state.center = coords

    m = folium.Map(location=st.session_state.center, zoom_start=18)

    # Logica Immagine Overlay
    if img_file:
        try:
            img = Image.open(img_file).convert("RGBA")
            if rotation != 0:
                img = img.rotate(-rotation, expand=True)
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            
            lat, lon = st.session_state.center
            bounds = [[lat - scale, lon - scale], [lat + scale, lon + scale]]
            ImageOverlay(image=f"data:image/png;base64,{b64}", bounds=bounds, opacity=opacity).add_to(m)
        except Exception as e:
            st.error(f"Errore overlay: {e}")

    # Marker Sensori
    for p in st.session_state.punti:
        nome_full = f"{p['dl']} | {p['nome']}"
        if nome_full in sensori_visibili:
            color = 'green' if nome_full == target else 'blue'
            folium.Marker(
                [p['lat'], p['lon']],
                popup=nome_full,
                icon=folium.Icon(color=color)
            ).add_to(m)

    # Rendering
    out = st_folium(m, width=1200, height=600)

    # Salvataggio coordinate al click
    if out and out.get("last_clicked") and target:
        new_lat = out["last_clicked"]["lat"]
        new_lon = out["last_clicked"]["lng"]
        dl, nome = target.split(" | ")
        
        st.session_state.punti = [p for p in st.session_state.punti if not (p['nome']==nome and p['dl']==dl)]
        st.session_state.punti.append({"dl": dl, "nome": nome, "lat": new_lat, "lon": new_lon})
        
        save_json(CONFIG_FILE, st.session_state.punti)
        st.rerun()

    # Tabella Dati
    with st.expander("📄 Dati Salvati"):
        if st.session_state.punti:
            st.dataframe(pd.DataFrame(st.session_state.punti), use_container_width=True)
            if st.button("🗑 Reset Totale"):
                st.session_state.punti = []
                save_json(CONFIG_FILE, [])
                st.rerun()

# --- ENTRY POINT ---
if __name__ == "__main__":
    run_map_manager()
