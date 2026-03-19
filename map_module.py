import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

def render_territorial():
    st.subheader("🌍 Posizionamento su Mappa GIS")
    st.write("Carica un file CSV/Excel con colonne 'Latitudine', 'Longitudine' e 'Nome Sensore'.")
    
    up_map = st.file_uploader("Carica dati geografici", type=["csv", "xlsx"], key="up_gis")
    
    if up_map:
        if up_map.name.endswith('.csv'):
            df_map = pd.read_csv(up_map)
        else:
            df_map = pd.read_excel(up_map)
            
        # Verifica se le colonne necessarie esistono
        cols = df_map.columns.tolist()
        lat_col = st.selectbox("Seleziona colonna Latitudine", cols)
        lon_col = st.selectbox("Seleziona colonna Longitudine", cols)
        name_col = st.selectbox("Seleziona colonna Nome Sensore", cols)
        
        if st.button("Visualizza Mappa"):
            fig = px.scatter_mapbox(df_map, lat=lat_col, lon=lon_col, hover_name=name_col,
                                    color_discrete_sequence=["fuchsia"], zoom=10, height=600)
            fig.update_layout(mapbox_style="open-street-map")
            fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

def render_structural():
    st.subheader("🏗️ Layout Strutturale su Immagine")
    st.write("Carica la planimetria o la foto della struttura per mappare i sensori.")
    
    img_file = st.file_uploader("Carica immagine struttura", type=["jpg", "png", "jpeg"], key="up_struct")
    
    if img_file:
        img = Image.open(img_file)
        width, height = img.size
        
        st.info("Clicca sui punti dell'immagine per identificare la posizione dei sensori (Funzionalità interattiva tramite Plotly)")
        
        # Usiamo Plotly per rendere l'immagine interattiva (permette di avere le coordinate del click)
        fig = px.imshow(img)
        
        # Se abbiamo già dei sensori salvati in session_state, li mostriamo
        if 'sensor_coords' not in st.session_state:
            st.session_state['sensor_coords'] = []
            
        # Aggiungiamo i punti esistenti sopra l'immagine
        if st.session_state['sensor_coords']:
            df_coords = pd.DataFrame(st.session_state['sensor_coords'])
            fig.add_scatter(x=df_coords['x'], y=df_coords['y'], mode='markers+text', 
                            marker=dict(color='red', size=12),
                            text=df_coords['name'], textposition="top center",
                            name="Sensori")

        fig.update_layout(
            dragmode='drawpoint', # Permette di interagire
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_showscale=False
        )
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=False)
        
        # Visualizzazione
        st.plotly_chart(fig, use_container_width=True)
        
        # Form per aggiungere un nuovo sensore inserendo le coordinate manualmente o logica futura
        with st.expander("Aggiungi / Modifica Sensore"):
            c1, c2, c3 = st.columns(3)
            new_name = c1.text_input("Nome Sensore")
            pos_x = c2.number_input("Coordinata X", value=0)
            pos_y = c3.number_input("Coordinata Y", value=0)
            if st.button("Salva Posizione"):
                st.session_state['sensor_coords'].append({'name': new_name, 'x': pos_x, 'y': pos_y})
                st.rerun()

        if st.button("Resetta tutto"):
            st.session_state['sensor_coords'] = []
            st.rerun()

def run_map_manager():
    # Questa è la funzione che richiamerai da app_DIMOS.py
    t1, t2 = st.tabs(["🌍 Mappa GIS (Territorio)", "🏗️ Layout Strutturale (Foto)"])
    
    with t1:
        render_territorial()
        
    with t2:
        render_structural()
