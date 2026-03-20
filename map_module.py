import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import io

def modulo_mappe_avanzato():
    st.header("🗺️ Gestione Spaziale Sensori (GIS & Planimetrie)")
    
    tipo_mappa = st.radio("Seleziona Tipo Visualizzazione", ["Mappa Geografica (OSM)", "Planimetria Tecnica (CAD/Immagine)"])

    if tipo_mappa == "Planimetria Tecnica (CAD/Immagine)":
        st.subheader("📍 Posizionamento su Immagine")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            img_file = st.file_uploader("1. Carica Planimetria (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
            excel_coords = st.file_uploader("2. Carica Coordinate Sensori (Excel)", type=['xlsx'])
            st.info("L'Excel deve avere le colonne: 'Nome', 'X', 'Y', 'Colore'")
            
            # Form per inserimento manuale/modifica veloce
            with st.expander("Aggiungi/Modifica Sensore"):
                new_name = st.text_input("Nome Sensore")
                new_x = st.number_input("Coordinata X", value=0.0)
                new_y = st.number_input("Coordinata Y", value=0.0)
                new_color = st.color_picker("Colore Marker", "#FF0000")

        with col2:
            if img_file:
                img = Image.open(img_file)
                w, h = img.size
                
                # Creiamo il contenitore per i sensori
                fig = go.Figure()

                # Carichiamo i dati dall'Excel se presente
                df_points = pd.DataFrame(columns=['Nome', 'X', 'Y', 'Colore'])
                if excel_coords:
                    df_points = pd.read_excel(excel_coords)
                
                # Se l'utente ha compilato il form manuale, aggiungiamolo temporaneamente
                if new_name:
                    new_row = pd.DataFrame([{'Nome': new_name, 'X': new_x, 'Y': new_y, 'Colore': new_color}])
                    df_points = pd.concat([df_points, new_row], ignore_index=True)

                # Sfondo: l'immagine CAD
                fig.add_layout_image(
                    dict(
                        source=img,
                        xref="x", yref="y",
                        x=0, y=h,
                        sizex=w, sizey=h,
                        sizing="stretch",
                        layer="below"
                    )
                )

                # Aggiungiamo i Marker (i sensori)
                if not df_points.empty:
                    fig.add_trace(go.Scatter(
                        x=df_points['X'],
                        y=df_points['Y'],
                        mode='markers+text',
                        marker=dict(size=14, color=df_points['Colore'] if 'Colore' in df_points else 'red', symbol='pentagon'),
                        text=df_points['Nome'],
                        textposition="top center",
                        hovertemplate="<b>%{text}</b><br>X: %{x}<br>Y: %{y}<extra></extra>"
                    ))

                # Impostazioni assi per mantenere le proporzioni dell'immagine
                fig.update_xaxes(showgrid=False, zeroline=False, range=[0, w])
                fig.update_yaxes(showgrid=False, zeroline=False, range=[0, h], scaleanchor="x")
                
                fig.update_layout(
                    width=900, height=700,
                    margin=dict(l=0, r=0, t=0, b=0),
                    dragmode='pan', # Permette di spostarsi nell'immagine
                )

                st.plotly_chart(fig, use_container_width=True)
                st.caption("Usa la barra degli strumenti in alto a destra per zoomare o misurare le distanze.")

    else:
        st.subheader("🌍 Mappa Geografica Interattiva")
        st.write("Qui integriamo la ricerca per città (Ancona) e i marker su coordinate reali.")
        # (Qui inseriremo il codice Folium con ricerca Nominatim)

# Chiamata alla funzione
# modulo_mappe_avanzato()
