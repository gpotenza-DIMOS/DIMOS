import streamlit as st
import pandas as pd
import json
import os
import requests
import base64
from streamlit_folium import st_folium
import folium
from folium import IFrame
from folium.raster_layers import ImageOverlay
from folium.features import DivIcon
from PIL import Image
from io import BytesIO

CONFIG_FILE = "mac_positions.json"

# ----------------- UTILS -----------------
def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_mac(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_MAC_DASHBOARD'}
        res = requests.get(url, headers=headers).json()
        if res:
            return float(res[0]['lat']), float(res[0]['lon'])
    except:
        return None
    return None

def parse_excel(file):
    xls = pd.ExcelFile(file)
    if "NAME" not in xls.sheet_names:
        return None

    df = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
    ana = {}
    for c in range(1, df.shape[1]):
        dl = str(df.iloc[0, c]).strip()
        sn = str(df.iloc[1, c]).strip()
        try:
            lat = float(df.iloc[3, c]) if df.iloc[3, c] != "" else None
            lon = float(df.iloc[4, c]) if df.iloc[4, c] != "" else None
        except:
            lat, lon = None, None
        if dl not in ana:
            ana[dl] = {}
        ana[dl][sn] = {"lat": lat, "lon": lon}
    return ana

# ----------------- MAIN -----------------
def run_map_manager():
    st.title("🌍 Dashboard MAC Interattiva")

    # ---------- GESTIONE EXCEL ----------
    with st.expander("📂 Carica o Cambia Excel", expanded='anagrafica' not in st.session_state):
        file_input = st.file_uploader("Carica Excel (Foglio NAME)", type=['xlsx', 'xlsm'])
        if file_input:
            ana = parse_excel(file_input)
            if ana:
                st.session_state['anagrafica'] = ana
                st.success("Excel caricato")
            else:
                st.error("Foglio NAME non trovato")
        if 'anagrafica' in st.session_state:
            if st.button("🔄 Cambia Excel"):
                del st.session_state['anagrafica']
                st.rerun()

    if 'anagrafica' not in st.session_state:
        st.stop()

    ana = st.session_state['anagrafica']
    punti_salvati = load_mac()

    # ---------- CONTROLLI SENSORI ----------
    col1, col2, col3 = st.columns(3)
    with col1:
        sel_dls = st.multiselect("📡 Filtra Datalogger", sorted(ana.keys()), default=sorted(ana.keys()))
    with col2:
        sensori_filtrati = [f"{d} | {s}" for d in sel_dls for s in ana[d].keys()]
        sensori_visibili = st.multiselect("👁️ Sensori visibili", sensori_filtrati, default=sensori_filtrati)
    with col3:
        target = st.selectbox("🎯 Sensore da posizionare", sensori_filtrati)

    # ---------- OVERLAY PLANIMETRIA ----------
    with st.expander("🖼️ Overlay Planimetria"):
        up_img = st.file_uploader("Carica immagine", type=['png', 'jpg', 'jpeg'])
        scale_slider = st.slider("Scala", 0.0001, 0.02, 0.002, 0.0001)
        rotation_slider = st.slider("Rotazione (°)", -180, 180, 0)
        opacity_slider = st.slider("Trasparenza", 0.0, 1.0, 0.5)

    # ---------- CENTRO MAPPA ----------
    if 'center' not in st.session_state:
        if punti_salvati:
            st.session_state.center = [punti_salvati[0]['lat'], punti_salvati[0]['lon']]
        else:
            st.session_state.center = [45.4642, 9.1900]

    city = st.text_input("🔍 Cerca città")
    if city:
        coords = get_coords(city)
        if coords:
            st.session_state.center = coords

    m = folium.Map(location=st.session_state.center, zoom_start=18)

    # ---------- OVERLAY IMAGE INTERATTIVO ----------
    if up_img:
        img = Image.open(up_img).convert("RGBA")
        w, h = img.size
        aspect_ratio = h / w
        if rotation_slider != 0:
            img = img.rotate(-rotation_slider, expand=True)
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64_img = base64.b64encode(buf.getvalue()).decode()
        lat, lon = st.session_state.center
        width = scale_slider
        height = scale_slider * aspect_ratio
        bounds = [[lat - height, lon - width], [lat + height, lon + width]]

        overlay = ImageOverlay(image=f"data:image/png;base64,{b64_img}", bounds=bounds, opacity=opacity_slider)
        overlay.add_to(m)

        # Aggiungiamo JS per rendere l'overlay trascinabile
        draggable_js = f"""
        <script>
        var img_layer = {overlay.get_name()};
        img_layer.on('add', function() {{
            img_layer.getElement().style.cursor = 'move';
            L.DomEvent.on(img_layer.getElement(), 'mousedown', function(e) {{
                var startLat = e.latlng ? e.latlng.lat : {lat};
                var startLng = e.latlng ? e.latlng.lng : {lon};
                var map = img_layer._map;
                function moveHandler(event) {{
                    var deltaLat = event.latlng.lat - startLat;
                    var deltaLng = event.latlng.lng - startLng;
                    var bounds = img_layer.getBounds();
                    var newBounds = [
                        [bounds.getSouthWest().lat + deltaLat, bounds.getSouthWest().lng + deltaLng],
                        [bounds.getNorthEast().lat + deltaLat, bounds.getNorthEast().lng + deltaLng]
                    ];
                    img_layer.setBounds(newBounds);
                }}
                map.on('mousemove', moveHandler);
                map.once('mouseup', function(){{ map.off('mousemove', moveHandler); }});
            }});
        }});
        </script>
        """
        m.get_root().html.add_child(folium.Element(draggable_js))

    # ---------- MARKER CON NOME ----------
    for p in punti_salvati:
        nome_full = f"{p['dl']} | {p['nome']}"
        is_visible = nome_full in sensori_visibili
        is_selected = target == nome_full
        if is_visible:
            folium.Marker(
                [p['lat'], p['lon']],
                icon=folium.Icon(color='blue' if is_selected else 'red'),
                tooltip=p['nome']
            ).add_to(m)
            # Aggiunge nome come testo sulla mappa
            folium.map.Marker(
                [p['lat'], p['lon']],
                icon=DivIcon(
                    icon_size=(150,36),
                    icon_anchor=(0,0),
                    html=f'<div style="font-size:12px;color:black;font-weight:bold">{p["nome"]}</div>',
                )
            ).add_to(m)

    # ---------- RENDER MAPPA ----------
    output = st_folium(m, width=1400, height=650)

    # ---------- CLICK SALVATAGGIO ----------
    if output.get("last_clicked") and target:
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        dl, nome = target.split(" | ")
        punti_salvati = [p for p in punti_salvati if not (p['nome']==nome and p['dl']==dl)]
        punti_salvati.append({"nome": nome, "lat": lat_c, "lon": lon_c, "dl": dl})
        save_mac(punti_salvati)
        st.rerun()

    # ---------- TABELLA DATI ----------
    if punti_salvati:
        with st.expander("📄 Dati Sensori"):
            st.dataframe(pd.DataFrame(punti_salvati))
            if st.button("🗑️ Reset Mappa"):
                save_mac([])
                st.rerun()

if __name__ == "__main__":
    run_map_manager()
