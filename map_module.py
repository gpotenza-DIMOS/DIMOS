import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
from geopy.geocoders import Nominatim
import os
from io import BytesIO

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(layout="wide", page_title="DIMOS Monitoraggio")

# --- FUNZIONE MAPPE (SISTEMATA) ---
def modulo_mappe(anagrafica_dati):
    st.subheader("🗺️ Gestione Spaziale e Planimetrie")
    
    if 'selected_sensor' not in st.session_state:
        st.session_state.selected_sensor = None

    tab1, tab2 = st.tabs(["🌍 Mappa Geografica", "🖼️ Planimetria CAD"])

    with tab1:
        city = st.text_input("Cerca Località (es. Ancona)", key="geo_search")
        lat, lon = 43.6158, 13.5189
        if city:
            try:
                geolocator = Nominatim(user_agent="dimos_app_final")
                loc = geolocator.geocode(city)
                if loc: lat, lon = loc.latitude, loc.longitude
            except: st.error("Errore connessione mappe.")
        
        fig_geo = go.Figure(go.Scattermapbox(lat=[lat], lon=[lon], mode='markers', marker=dict(size=15, color='blue')))
        fig_geo.update_layout(mapbox=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=12), margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_geo, use_container_width=True)

    with tab2:
        st.write("Carica il CAD e l'Excel con le colonne: **Nome, X, Y**")
        up_img = st.file_uploader("1. Carica Immagine CAD", type=['png', 'jpg', 'jpeg'])
        up_coord = st.file_uploader("2. Carica Excel Coordinate", type=['xlsx'])

        if up_img and up_coord:
            img = Image.open(up_img)
            w, h = img.size
            df_c = pd.read_excel(up_coord)
            
            fig_cad = go.Figure()
            fig_cad.add_layout_image(dict(source=img, xref="x", yref="y", x=0, y=h, sizex=w, sizey=h, sizing="stretch", layer="below"))
            
            fig_cad.add_trace(go.Scatter(
                x=df_c['X'], y=df_c['Y'], mode='markers+text',
                text=df_c['Nome'], marker=dict(size=20, color='red', symbol='diamond'),
                customdata=df_c['Nome']
            ))
            fig_cad.update_xaxes(range=[0, w], visible=False)
            fig_cad.update_yaxes(range=[0, h], visible=False, scaleanchor="x")
            fig_cad.update_layout(width=1000, height=700, margin=dict(l=0,r=0,t=0,b=0))

            # Cattura Click
            sel = st.plotly_chart(fig_cad, use_container_width=True, on_select="rerun")
            if sel and "selection" in sel and sel["selection"]["points"]:
                nome = sel["selection"]["points"][0]["customdata"]
                st.session_state.selected_sensor = nome
                st.success(f"✅ Selezionato: {nome}. Vai in 'Grafici'!")

# --- FUNZIONE GRAFICI (LA TUA ORIGINALE) ---
def modulo_grafici(anagrafica, df_f):
    st.subheader("📈 Analisi Dati")
    # Qui usiamo la selezione dalla mappa se esiste
    default_s = []
    if st.session_state.selected_sensor:
        # Cerchiamo di ricostruire la stringa "Datalogger | Sensore"
        for dl in anagrafica:
            for s in anagrafica[dl]:
                if s == st.session_state.selected_sensor:
                    default_s = [f"{dl} | {s}"]

    c1, c2, c3 = st.columns(3)
    with c1: sel_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    opts_s = [f"{d} | {s}" for d in sel_dls for s in anagrafica[d].keys()]
    with c2: sel_sens = st.multiselect("Sensori", opts_s, default=default_s)
    
    # ... resto del tuo codice per i grafici (Gauss, Trend, ecc.) ...
    st.write("Seleziona i sensori sopra per visualizzare i dati.")

# --- MAIN ---
def main():
    st.sidebar.title("DIMOS Navigation")
    menu = st.sidebar.radio("Vai a:", ["Home", "Grafici", "Mappe"])

    # Caricamento file (NAME)
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])
    
    if file_input:
        xls = pd.ExcelFile(file_input)
        # Mappatura anagrafica (Logica che preferisci)
        anagrafica = {}
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        for c_idx in range(1, df_name.shape[1]):
            dl = str(df_name.iloc[0, c_idx]).strip()
            sens = str(df_name.iloc[1, c_idx]).strip()
            web = str(df_name.iloc[2, c_idx]).strip()
            if dl == "nan" or web == "nan": continue
            if dl not in anagrafica: anagrafica[dl] = {}
            if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
            grand = web.split("_")[-1] if "_" in web else web
            anagrafica[dl][sens][grand] = web

        if menu == "Mappe":
            modulo_mappe(anagrafica) # QUI PASSO L'ARGOMENTO CHE MANCAVA
        elif menu == "Grafici":
            # Caricamento dati per grafici
            df = pd.read_excel(xls, sheet_name=xls.sheet_names[2]) # o il tuo foglio dati
            df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])
            modulo_grafici(anagrafica, df)
    else:
        st.info("Carica il file Excel per iniziare.")

if __name__ == "__main__":
    main()
