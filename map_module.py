import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from PIL import Image
import numpy as np
import tifffile
import json
import base64
import os

CONFIG_FILE = "mac_positions.json"

# ---------------- UTILS ----------------
def load_mac():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_mac(data):
    with open(CONFIG_FILE,"w") as f:
        json.dump(data, f, indent=4)

def img_to_data_url(img):
    """Convert PIL image to base64 data URL for folium overlay"""
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"

# ---------------- APP -----------------
def run_app():

    st.set_page_config(layout="wide")
    st.title("📍 GIS Avanzato: Mappe, Immagini, GeoTIFF, CAD/SVG")

    # ---------- SESSION STATE ----------
    if 'punti' not in st.session_state:
        st.session_state.punti = load_mac()
    if 'overlays' not in st.session_state:
        st.session_state.overlays = []

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.header("📥 Carica File")
        img_file = st.file_uploader("Immagine (PNG/JPG)", type=["png","jpg","jpeg"])
        geotiff_file = st.file_uploader("GeoTIFF", type=["tif","tiff"])
        svg_file = st.file_uploader("SVG / DXF convertito", type=["svg"])
        if st.button("🔄 Reset Tutto"):
            st.session_state.punti = {}
            st.session_state.overlays = []
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            st.experimental_rerun()

    # ---------- MAPPA ----------
    center = [45.4642, 9.1900]
    m = folium.Map(location=center, zoom_start=17)

    # ---------- OVERLAY IMMAGINI PNG/JPG ----------
    if img_file:
        img = Image.open(img_file)
        img_url = img_to_data_url(img)
        bounds = [[45.4635,9.1895],[45.4650,9.1910]]
        overlay_js = f"""
        <script src="https://unpkg.com/leaflet-distortableimage"></script>
        <script>
        var map = window.map_{id(m)};
        var overlay = new L.DistortableImageOverlay(
            "{img_url}",
            {{
                corners: [
                    [{bounds[0][0]}, {bounds[0][1]}],
                    [{bounds[0][0]}, {bounds[1][1]}],
                    [{bounds[1][0]}, {bounds[1][1]}],
                    [{bounds[1][0]}, {bounds[0][1]}]
                ],
                opacity: 0.7,
                selected: true
            }}
        ).addTo(map);
        </script>
        """
        m.get_root().html.add_child(folium.Element(overlay_js))
        st.success("Overlay immagine PNG/JPG caricato e scalabile/rotabile")

    # ---------- GEO TIFF ----------
    if geotiff_file:
        img_array = tifffile.imread(geotiff_file)
        if img_array.ndim == 2:
            img_array = np.stack([img_array]*3, axis=-1)
        img = Image.fromarray(img_array)
        bounds = [[45.4635,9.1895],[45.4650,9.1910]]
        img_url = img_to_data_url(img)
        overlay_js = f"""
        <script src="https://unpkg.com/leaflet-distortableimage"></script>
        <script>
        var map = window.map_{id(m)};
        var overlay = new L.DistortableImageOverlay(
            "{img_url}",
            {{
                corners: [
                    [{bounds[0][0]}, {bounds[0][1]}],
                    [{bounds[0][0]}, {bounds[1][1]}],
                    [{bounds[1][0]}, {bounds[1][1]}],
                    [{bounds[1][0]}, {bounds[0][1]}]
                ],
                opacity: 0.7,
                selected: true
            }}
        ).addTo(map);
        </script>
        """
        m.get_root().html.add_child(folium.Element(overlay_js))
        st.success("GeoTIFF caricato e scalabile/rotabile")

    # ---------- SVG ----------
    if svg_file:
        svg_data = svg_file.read().decode()
        img_url = "data:image/svg+xml;base64," + base64.b64encode(svg_data.encode()).decode()
        bounds = [[45.4635,9.1895],[45.4650,9.1910]]
        overlay_js = f"""
        <script src="https://unpkg.com/leaflet-distortableimage"></script>
        <script>
        var map = window.map_{id(m)};
        var overlay = new L.DistortableImageOverlay(
            "{img_url}",
            {{
                corners: [
                    [{bounds[0][0]}, {bounds[0][1]}],
                    [{bounds[0][0]}, {bounds[1][1]}],
                    [{bounds[1][0]}, {bounds[1][1]}],
                    [{bounds[1][0]}, {bounds[0][1]}]
                ],
                opacity: 0.7,
                selected: true
            }}
        ).addTo(map);
        </script>
        """
        m.get_root().html.add_child(folium.Element(overlay_js))
        st.success("SVG caricato e scalabile/rotabile")

    # ---------- MARKER EDITABLE ----------
    for k,p in st.session_state.punti.items():
        folium.Marker([p["lat"],p["lon"]],
                      tooltip=p.get("label",f"{p['lat']},{p['lon']}"),
                      draggable=True).add_to(m)

    # plugin Draw per aggiungere/eliminare marker
    Draw(export=True, filename="map_export.geojson").add_to(m)

    # ---------- VISUALIZZA MAPPA ----------
    map_data = st_folium(m, width=1000, height=700)

    # Salva marker click
    if map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        key = f"Punto_{len(st.session_state.punti)+1}"
        st.session_state.punti[key] = {"lat":lat,"lon":lon,"label":f"{lat:.5f},{lon:.5f}"}
        save_mac(st.session_state.punti)
        st.success(f"Aggiunto marker in {lat:.5f},{lon:.5f}")

if __name__=="__main__":
    run_app()
