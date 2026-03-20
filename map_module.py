import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os

CONFIG_FILE = "gis_positions.json"

def load_gis():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    return []

def save_gis(data):
    with open(CONFIG_FILE, "w") as f: json.dump(data, f)

def run_map_manager():
    st.header("🌍 Mappa Territoriale Interattiva")

    # --- 1. CONTROLLI DI NAVIGAZIONE ---
    with st.sidebar:
        st.subheader("🚀 Vai a...")
        search_city = st.text_input("Cerca Località (es. Ancona)")
        
        st.write("--- oppure ---")
        lat_manual = st.number_input("Latitudine", value=43.6158, format="%.6f")
        lon_manual = st.number_input("Longitudine", value=13.5189, format="%.6f")
        zoom_level = st.slider("Zoom", 1, 20, 12)

        st.divider()
        st.subheader("🛠️ Inserimento Sensore")
        nome_bastardo = st.text_input("Nome Sensore", value="Pippo_01")
        st.info("Clicca sulla mappa per posizionare il sensore col nome scritto sopra.")

    # --- 2. GESTIONE POSIZIONI ---
    punti_salvati = load_gis()
    
    # Se cerchi una città (Logica semplificata senza librerie extra per non farti crashare)
    # Nota: In produzione qui useremmo geopy, ma per ora usiamo i valori manuali
    curr_lat, curr_lon = lat_manual, lon_manual

    # --- 3. CREAZIONE MAPPA ---
    # Creiamo un DataFrame dai punti salvati
    if punti_salvati:
        df_punti = pd.DataFrame(punti_salvati)
    else:
        df_punti = pd.DataFrame(columns=['Nome', 'Lat', 'Lon'])

    fig = px.scatter_mapbox(
        df_punti,
        lat="Lat",
        lon="Lon",
        text="Nome",
        hover_name="Nome",
        zoom=zoom_level,
        center={"lat": curr_lat, "lon": curr_lon},
        mapbox_style="open-street-map"
    )

    fig.update_traces(marker=dict(size=15, color="red", symbol="marker"))
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)

    # --- 4. CATTURA CLICK ---
    st.write(f"Stai posizionando: **{nome_bastardo}**")
    click_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    if click_data and "selection" in click_data and click_data["selection"]["points"]:
        # Se l'utente clicca su un punto esistente, non facciamo nulla o lo modifichiamo
        pass
    
    # Per il posizionamento NUOVO su Mapbox con Plotly Streamlit 
    # usiamo un trucco: prendiamo le coordinate del centro mappa se l'utente conferma
    if st.button(f"📍 Conferma Posizione '{nome_bastardo}' qui al centro"):
        nuovo_punto = {"Nome": nome_bastardo, "Lat": curr_lat, "Lon": curr_lon}
        punti_salvati.append(nuovo_punto)
        save_gis(punti_salvati)
        st.success(f"Sensore {nome_bastardo} salvato!")
        st.rerun()

    if st.button("🗑️ Svuota Mappa Mondiale"):
        save_gis([])
        st.rerun()

    # Tabella riassuntiva
    if punti_salvati:
        with st.expander("Elenco Coordinate Salvate"):
            st.table(df_punti)
