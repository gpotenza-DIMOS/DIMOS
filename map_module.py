import streamlit as st
from streamlit_folium import st_folium
import folium
from PIL import Image

def render_mappa_territoriale(df_sensori):
    st.subheader("📍 Posizionamento Sensori su Mappa")
    # Centro mappa (es. Italia o media coordinate)
    m = folium.Map(location=[45.0, 9.0], zoom_start=6)
    
    # Se il file ha coordinate, le disegna
    for index, row in df_sensori.iterrows():
        folium.Marker(
            [row['lat'], row['lon']], 
            popup=f"Sensore: {row['ID']}",
            tooltip=row['ID']
        ).add_to(m)
    
    # Cattura il click per posizionamento manuale
    st_data = st_folium(m, width=700)
    if st_data["last_clicked"]:
        st.write(f"Coordinate selezionate: {st_data['last_clicked']}")

def render_mappa_strutturale(uploaded_image):
    st.subheader("🏗️ Layout Sensori su Struttura")
    img = Image.open(uploaded_image)
    st.image(img, caption="Planimetria della struttura")
    
    # Qui useremmo una libreria come 'streamlit-cropper' o 'bokeh' 
    # per permetterti di cliccare sulla foto e salvare le coordinate X,Y
    st.info("Clicca sulla foto per assegnare la posizione ai sensori selezionati.")
