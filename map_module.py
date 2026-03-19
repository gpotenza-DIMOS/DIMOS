import streamlit as st
import pandas as pd
import plotly.express as px
import io

def render_territorial():
    st.subheader("🌍 Posizionamento su Mappa GIS")
    st.write("Carica un file CSV/Excel con le coordinate dei sensori.")
    
    up_map = st.file_uploader("Carica dati geografici", type=["csv", "xlsx"], key="up_gis")
    
    if up_map:
        try:
            if up_map.name.endswith('.csv'):
                df_map = pd.read_csv(up_map)
            else:
                df_map = pd.read_excel(up_map)
                
            cols = df_map.columns.tolist()
            c1, c2, c3 = st.columns(3)
            lat_col = c1.selectbox("Latitudine", cols)
            lon_col = c2.selectbox("Longitudine", cols)
            name_col = c3.selectbox("Etichetta", cols)
            
            fig = px.scatter_mapbox(df_map, lat=lat_col, lon=lon_col, hover_name=name_col,
                                    color_discrete_sequence=["#ff0000"], zoom=12, height=500)
            fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Errore nel caricamento dati: {e}")

def render_structural():
    st.subheader("🏗️ Layout Strutturale")
    st.info("Carica una foto della struttura. Passa il mouse sull'immagine per leggere le coordinate (x, y) e aggiungi i sensori.")
    
    img_file = st.file_uploader("Seleziona immagine struttura", type=["jpg", "png", "jpeg"], key="up_struct")
    
    if img_file:
        # Leggiamo l'immagine senza Pillow (PIL) usando direttamente i bytes per evitare errori di modulo
        img_bytes = img_file.read()
        
        if 'sensor_coords' not in st.session_state:
            st.session_state['sensor_coords'] = []
            
        # Creiamo il grafico Plotly con l'immagine di sfondo
        import plotly.graph_objects as go
        from PIL import Image
        
        # Uso io.BytesIO per gestire l'immagine
        image = Image.open(io.BytesIO(img_bytes))
        width, height = image.size

        fig = go.Figure()

        # Aggiungi immagine come sfondo
        fig.add_layout_image(
            dict(
                source=image,
                xref="x", yref="y",
                x=0, y=height,
                sizex=width, sizey=height,
                sizing="stretch",
                layer="below"
            )
        )

        # Configura assi
        fig.update_xaxes(range=[0, width], showgrid=False, zeroline=False, visible=False)
        fig.update_yaxes(range=[0, height], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1)

        # Disegna i sensori già salvati
        if st.session_state['sensor_coords']:
            df = pd.DataFrame(st.session_state['sensor_coords'])
            fig.add_trace(go.Scatter(
                x=df['x'], y=df['y'],
                mode='markers+text',
                marker=dict(color='#ff0000', size=15, symbol='circle', line=dict(color='white', width=2)),
                text=df['name'],
                textposition="top center",
                name="Sensori"
            ))

        fig.update_layout(
            width=width, height=height,
            margin=dict(l=0, r=0, t=0, b=0),
            hovermode='closest'
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # Pannello di controllo sensori
        with st.container(border=True):
            st.markdown("#### Gestione Punti di Monitoraggio")
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            new_name = c1.text_input("Identificativo Sensore (es. S01)")
            pos_x = c2.number_input("Coordinata X", value=0)
            pos_y = c3.number_input("Coordinata Y", value=0)
            
            if c4.button("➕ AGGIUNGI", use_container_width=True):
                if new_name:
                    st.session_state['sensor_coords'].append({'name': new_name, 'x': pos_x, 'y': pos_y})
                    st.rerun()
                else:
                    st.warning("Inserisci un nome!")

        if st.button("🗑️ RESETTA LAYOUT"):
            st.session_state['sensor_coords'] = []
            st.rerun()

def run_map_manager():
    # Stile per i tab per richiamare il rosso Microgeo
    st.markdown("""
        <style>
            button[data-baseweb="tab"] { font-size: 18px; font-weight: bold; }
            button[aria-selected="true"] { color: #ff0000 !important; border-bottom-color: #ff0000 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["🌍 MONITORAGGIO TERRITORIALE", "🏗️ LAYOUT STRUTTURALE"])
    
    with t1:
        render_territorial()
    with t2:
        render_structural()
