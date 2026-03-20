import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import os
import json

CONFIG_FILE = "sensor_positions.json"

def load_positions():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_positions(positions):
    with open(CONFIG_FILE, "w") as f:
        json.dump(positions, f)

def run_map_manager():
    st.header("📍 Centro Controllo Mappe")

    # --- RECUPERO SENSORI (Excel o Manuali) ---
    sensori_disponibili = []
    
    # Se l'excel è caricato nel plotter, prendiamo quelli
    if 'df_values' in st.session_state:
        df = st.session_state['df_values']
        col_t = st.session_state.get('col_tempo', 'Data e Ora')
        sensori_disponibili = [c for c in df.columns if c != col_t]
    
    # Permettiamo SEMPRE l'inserimento manuale (es. Pippo)
    st.sidebar.subheader("➕ Inserimento Manuale")
    nuovo_s = st.sidebar.text_input("Nome Sensore Manuale")
    if st.sidebar.button("Aggiungi all'elenco"):
        if nuovo_s and nuovo_s not in sensori_disponibili:
            if 'manual_list' not in st.session_state: st.session_state.manual_list = []
            st.session_state.manual_list.append(nuovo_s)
    
    # Uniamo le liste
    if 'manual_list' in st.session_state:
        sensori_disponibili += st.session_state.manual_list

    if not sensori_disponibili:
        st.info("💡 Inserisci un nome nel menu a sinistra o carica un Excel nei Grafici per iniziare.")
        return

    posizioni_salvate = load_positions()

    # --- INTERFACCIA MAPPA ---
    col_sel, col_map = st.columns([1, 4])
    
    with col_sel:
        sensore_da_piazzare = st.selectbox("Seleziona sensore da posizionare:", sensori_disponibili)
        img_sfondo = st.file_uploader("Carica Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        if st.button("Svuota Posizioni Salve"):
            save_positions({})
            st.rerun()

    with col_map:
        fig = go.Figure()
        
        if img_sfondo:
            img = Image.open(img_sfondo)
            w, h = img.size
            fig.add_layout_image(dict(
                source=img, xref="x", yref="y", x=0, y=h, 
                sizex=w, sizey=h, sizing="stretch", layer="below"
            ))
            fig.update_xaxes(range=[0, w], visible=True)
            fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
        else:
            w, h = 1000, 1000
            fig.update_xaxes(range=[0, w])
            fig.update_yaxes(range=[0, h], scaleanchor="x")
            st.warning("Carica un'immagine per lo sfondo CAD.")

        # Disegna i sensori già salvati
        current_map_pos = posizioni_salvate.get("image", {})
        for s_name, coords in current_map_pos.items():
            fig.add_trace(go.Scatter(
                x=[coords['x']], y=[coords['y']],
                mode="markers+text",
                text=[s_name],
                marker=dict(size=12, color="red", symbol="diamond"),
                name=s_name,
                textposition="top center"
            ))

        # Gestione del Click per posizionare il sensore selezionato
        st.write(f"Clicca sulla mappa per posizionare: **{sensore_da_piazzare}**")
        selected_point = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        
        if selected_point and "selection" in selected_point and selected_point["selection"]["points"]:
            pt = selected_point["selection"]["points"][0]
            # Salvataggio coordinate
            if "image" not in posizioni_salvate: posizioni_salvate["image"] = {}
            posizioni_salvate["image"][sensore_da_piazzare] = {"x": pt['x'], "y": pt['y']}
            save_positions(posizioni_salvate)
            st.success(f"Posizionato {sensore_da_piazzare} a X:{int(pt['x'])} Y:{int(pt['y'])}")
            st.rerun()
