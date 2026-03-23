import streamlit as st
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
import json, os
import pandas as pd
import re
from PIL import Image
import numpy as np
import rasterio
import shapely.geometry as geom
import ezdxf

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

def parse_web_name(web):
    parts = re.sub(r"\[.*?\]","",web).split()
    dl = parts[0] if len(parts)>0 else "UNKNOWN"
    sn = parts[1] if len(parts)>1 else "UNKNOWN"
    return dl, sn

# -------------- APP -----------------
def run_app():

    st.set_page_config(layout="wide")
    st.title("📍 Visualizzatore Mappe, Immagini, GeoTIFF, CAD")

    if 'punti' not in st.session_state:
        st.session_state.punti = load_mac()

    # setup input
    with st.sidebar:
        st.header("📥 Carica File")

        img_file = st.file_uploader("Immagine (JPG/PNG)", type=["jpg","jpeg","png"])
        geotiff_file = st.file_uploader("Geotiff", type=["tif","tiff"])
        dxf_file = st.file_uploader("CAD (DWG/DXF/SVG)", type=["dxf","dwg","svg"])

        if st.button("🔄 Reset TUTTO"):
            st.session_state.punti = {}
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            st.experimental_rerun()

    # ---------------- MAPPA ----------------
    center=[45.4642, 9.1900]
    m = folium.Map(location=center, zoom_start=17)

    #### Image Overlay JPG/PNG
    if img_file:
        img = Image.open(img_file)
        arr = np.array(img)
        bounds = st.slider("Modifica Bounding Box Immagine",
                          value=((45.4635,9.1895),(45.4650,9.1910)))
        folium.raster_layers.ImageOverlay(
            image=arr,
            bounds=bounds,
            opacity=st.slider("Trasparenza Immagine",0.0,1.0,0.6)
        ).add_to(m)
        st.info(f"Overlay immagine caricata: bounding {bounds}")

    #### Geotiff
    if geotiff_file:
        with rasterio.open(geotiff_file) as src:
            img = src.read()  # bands
            bounds = src.bounds
            box = [[bounds.bottom,bounds.left],[bounds.top,bounds.right]]
            img = np.transpose(img, (1,2,0))
            folium.raster_layers.ImageOverlay(
                image=img,
                bounds=box,
                opacity=st.slider("Trasparenza GeoTIFF", 0.0,1.0,0.7)
            ).add_to(m)
        st.success("GeoTIFF visualizzato")

    #### CAD DXF
    if dxf_file:
        ext = dxf_file.name.split(".")[-1].lower()
        if ext in ["dxf","dwg"]:
            try:
                doc = ezdxf.readfile(dxf_file)
                msp = doc.modelspace()
                for line in msp.query("LINE"):
                    start = (line.dxf.start.y, line.dxf.start.x)
                    end = (line.dxf.end.y, line.dxf.end.x)
                    folium.PolyLine([start,end],color="blue").add_to(m)
                st.success("CAD DXF visualizzato come linee")
            except Exception as e:
                st.error(f"Errore lettura DXF/DWG: {e}")
        elif ext=="svg":
            svg_data = dxf_file.read().decode()
            folium.raster_layers.ImageOverlay(
                image=svg_data,
                bounds=st.slider("Bounding SVG",((45.4635,9.1895),(45.4650,9.1910))),
                opacity=st.slider("Trasparenza SVG",0.0,1.0,0.6)
            ).add_to(m)
            st.success("SVG visualizzato")

    # ---- Marker su Mappa ----
    for k,p in st.session_state.punti.items():
        folium.Marker([p["lat"],p["lon"]],tooltip=p["label"]).add_to(m)

    # render
    st_data = st_folium(m, width="100%",height=700)

    if st_data.get("last_clicked"):
        lat = st_data["last_clicked"]["lat"]
        lon = st_data["last_clicked"]["lng"]
        st.session_state.punti[f"Punto_{len(st.session_state.punti)+1}"]={
            "lat":lat,"lon":lon,"label":f"{lat:.5f},{lon:.5f}"
        }
        save_mac(st.session_state.punti)
        st.success(f"Aggiunto marker in {lat:.5f},{lon:.5f}")

if __name__=="__main__":
    run_app()
