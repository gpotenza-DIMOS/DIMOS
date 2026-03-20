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

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="MAC PRO Dashboard", layout="wide", page_icon="🌍")

CONFIG_FILE = "mac_positions.json"
OVERLAY_FILE = "overlay_config.json"

# --- CSS CUSTOM PER UN LOOK PRO ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stExpander { background-color: white; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ------------------ UTILS ------------------
def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

@st.cache_data
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'MAC_PRO_v2'}
        res = requests.get(url, headers=headers).json()
        return (float(res[0]['lat']), float(res[0]['lon'])) if res else None
    except: return None

# ------------------ LOGICA CORE ------------------
def parse_excel(file):
    try:
        xls = pd.ExcelFile(file)
        if "NAME" not in xls.sheet_names:
            return None
        df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
        ana = {}
        # Partiamo dalla colonna 1 (B)
        for c in range(1, df.shape[1]):
            dl = str(df.iloc[0, c]).strip()
            sn = str(df.iloc[1, c]).strip()
            if not dl or dl == "nan": continue
            
            if dl not in ana: ana[dl] = {}
            ana[dl][sn] = {"lat": None, "lon": None}
        return ana
    except Exception as e:
        st.error(f"Errore lettura Excel: {e}")
        return None

def main():
    st.title("🌍 Dashboard MAC PRO | Geo-Intelligence")
    
    # Inizializzazione Session State
    if 'punti' not in st.session_state:
        saved = load_json(CONFIG_FILE)
        st.session_state.punti = saved if isinstance(saved, list) else []
    if 'center' not in st.session_state:
        st.session_state.center = [45.4642, 9.1900]

    # --- SIDEBAR: CONTROLLI ESTRATTI ---
    with st.sidebar:
        st.header("⚙️ Impostazioni")
        file_input = st.file_uploader("1. Carica Configurazione (Excel)", type=['xlsx','xlsm'])
        
        if file_input:
            ana = parse_excel(file_input)
            if ana:
                st.session_state['anagrafica'] = ana
                st.success("Dati caricati con successo!")

        if 'anagrafica' in st.session_state:
            ana = st.session_state['anagrafica']
            
            st.divider()
            sel_dls = st.multiselect("📡 Filtra Datalogger", list(ana.keys()), default=list(ana.keys()))
            
            sensori_disp = [f"{d} | {s}" for d in sel_dls for s in ana[d]]
            st.session_state.sensori_visibili = st.multiselect("👁️ Mostra sulla mappa", sensori_disp, default=sensori_disp)
            
            st.session_state.target = st.selectbox("🎯 Seleziona per posizionare", sensori_disp)
            
            st.divider()
            if st.button("🗑 Svuota Mappa"):
                st.session_state.punti = []
                save_json(CONFIG_FILE, [])
                st.rerun()

    if 'anagrafica' not in st.session_state:
        st.info("👈 Inizia caricando un file Excel dalla sidebar.")
        st.stop()

    # --- LAYOUT PRINCIPALE ---
    col_map, col_ctrl = st.columns([3, 1])

    with col_ctrl:
        with st.expander("🖼️ Overlay GIS", expanded=False):
            img_file = st.file_uploader("Immagine Planimetria", type=["png","jpg"])
            conf = load_json(OVERLAY_FILE)
            scale = st.slider("Scala", 0.0001, 0.05, conf.get("scale", 0.002), format="%.4f")
            rot = st.slider("Rotazione", -180, 180, conf.get("rotation", 0))
            opac = st.slider("Opacità", 0.0, 1.0, conf.get("opacity", 0.5))
            if st.button("💾 Salva Overlay"):
                save_json(OVERLAY_FILE, {"scale": scale, "rotation": rot, "opacity": opac})

        city = st.text_input("🔍 Vai a città...", placeholder="es: Milano")
        if city:
            new_coords = get_coords(city)
            if new_coords: st.session_state.center = new_coords

    with col_map:
        m = folium.Map(location=st.session_state.center, zoom_start=18, tiles="OpenStreetMap")

        # Overlay Logic
        if img_file:
            img = Image.open(img_file).convert("RGBA")
            if rot != 0: img = img.rotate(-rot, expand=True)
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            
            bounds = [
                [st.session_state.center[0] - scale, st.session_state.center[1] - scale],
                [st.session_state.center[0] + scale, st.session_state.center[1] + scale]
            ]
            ImageOverlay(image=f"data:image/png;base64,{b64}", bounds=bounds, opacity=opac).add_to(m)

        # Disegna Marker
        for p in st.session_state.punti:
            tag = f"{p['dl']} | {p['nome']}"
            if tag in st.session_state.sensori_visibili:
                color = 'green' if tag == st.session_state.target else 'blue'
                folium.Marker(
                    [p['lat'], p['lon']], 
                    popup=tag, 
                    icon=folium.Icon(color=color, icon='info-sign')
                ).add_to(m)

        # Render Mappa
        out = st_folium(m, width="100%", height=600, key="main_map")

    # --- LOGICA DI SALVATAGGIO ---
    if out and out.get("last_clicked"):
        new_lat, new_lon = out["last_clicked"]["lat"], out["last_clicked"]["lng"]
        dl, nome = st.session_state.target.split(" | ")
        
        # Aggiorna o Aggiungi
        st.session_state.punti = [p for p in st.session_state.punti if not (p['nome']==nome and p['dl']==dl)]
        st.session_state.punti.append({"dl": dl, "nome": nome, "lat": new_lat, "lon": new_lon})
        
        save_json(CONFIG_FILE, st.session_state.punti)
        st.rerun()

    # --- TABELLA DATI FINALI ---
    with st.expander("📊 Riepilogo Coordinate"):
        if st.session_state.punti:
            final_df = pd.DataFrame(st.session_state.punti)
            st.dataframe(final_df, use_container_width=True)
            
            # Esportazione
            json_str = json.dumps(st.session_state.punti, indent=4)
            st.download_button("📥 Scarica JSON", data=json_str, file_name="posizioni_mac.json", mime="application/json")
        else:
            st.write("Nessun punto posizionato.")

if __name__ == "__main__":
    main()
