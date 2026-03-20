import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import os

st.set_page_config(layout="wide", page_title="DIMOS Hub")

# --- STATO DELLA SESSIONE (Per non perdere i sensori inseriti a mano) ---
if 'manual_sensors' not in st.session_state:
    st.session_state.manual_sensors = [] # Lista di dizionari {'Nome':..., 'X':..., 'Y':...}

def run_app():
    st.sidebar.title("📌 DIMOS Nav")
    menu = st.sidebar.radio("Seleziona:", ["Mappe", "Grafici"])
    
    # Caricamento file opzionale
    file_input = st.sidebar.file_uploader("Carica Excel (Opzionale)", type=['xlsx', 'xlsm'])

    if menu == "Mappe":
        st.header("🗺️ Posizionamento Manuale e Planimetrie")
        
        c1, c2 = st.columns([1, 3])
        
        with c1:
            st.subheader("🛠️ Inserimento Manuale")
            nome_nuovo = st.text_input("Nome Sensore (es. Pippo)")
            x_nuovo = st.number_input("Coordinata X", value=0)
            y_nuovo = st.number_input("Coordinata Y", value=0)
            
            if st.button("Aggiungi Sensore"):
                if nome_nuovo:
                    st.session_state.manual_sensors.append({'Nome': nome_nuovo, 'X': x_nuovo, 'Y': y_nuovo})
                    st.success(f"Aggiunto {nome_nuovo}")

            if st.button("Svuota Mappa"):
                st.session_state.manual_sensors = []
                st.rerun()

            st.divider()
            img_file = st.file_uploader("Sfondo: Carica Immagine/CAD", type=['png', 'jpg', 'jpeg'])

        with c2:
            fig = go.Figure()

            # Se c'è un'immagine, la mettiamo come sfondo
            if img_file:
                img = Image.open(img_file)
                w, h = img.size
                fig.add_layout_image(dict(
                    source=img, xref="x", yref="y", x=0, y=h, sizex=w, sizey=h,
                    sizing="stretch", layer="below"
                ))
                fig.update_xaxes(range=[0, w], visible=True)
                fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
            else:
                # Altrimenti usiamo una griglia standard 1000x1000
                fig.update_xaxes(range=[0, 1000], title="X")
                fig.update_yaxes(range=[0, 1000], title="Y", scaleanchor="x")
                st.info("Nessuna immagine caricata. Uso griglia standard (0-1000).")

            # Disegniamo i sensori dalla lista manuale
            if st.session_state.manual_sensors:
                df_manual = pd.DataFrame(st.session_state.manual_sensors)
                fig.add_trace(go.Scatter(
                    x=df_manual['X'], y=df_manual['Y'],
                    mode='markers+text',
                    text=df_manual['Nome'],
                    marker=dict(size=15, color='red', symbol='diamond'),
                    name="Manuale"
                ))

            fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0), dragmode='drawpoint')
            
            st.plotly_chart(fig, use_container_width=True)

    elif menu == "Grafici":
        st.info("Modulo Grafici. Carica un file Excel per vedere i dati reali.")

if __name__ == "__main__":
    run_app()
