import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(layout="wide", page_title="DIMOS - Sistema Unificato")

# Inizializziamo subito lo stato per evitare crash di variabili mancanti
if 'punti_manuali' not in st.session_state:
    st.session_state.punti_manuali = []
if 'anagrafica' not in st.session_state:
    st.session_state.anagrafica = None

# --- 2. DEFINIZIONE MODULI (SCRITTI PRIMA DEL MAIN) ---

def modulo_mappe():
    st.header("🗺️ Mappe e Planimetrie")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("📍 Inserimento Manuale")
        # Qui puoi scrivere "Pippo" o quello che vuoi
        nome = st.text_input("Nome Sensore", value="Pippo")
        x = st.number_input("Coordinata X", value=0)
        y = st.number_input("Coordinata Y", value=0)
        
        if st.button("Posiziona"):
            st.session_state.punti_manuali.append({'Nome': nome, 'X': x, 'Y': y})
            st.rerun()
        
        if st.button("🗑️ Reset"):
            st.session_state.punti_manuali = []
            st.rerun()
            
        st.divider()
        img_file = st.file_uploader("🖼️ Carica CAD o Immagine", type=['png', 'jpg', 'jpeg'])

    with col2:
        fig = go.Figure()
        
        # Gestione Sfondo
        if img_file:
            img = Image.open(img_file)
            w, h = img.size
            fig.add_layout_image(dict(source=img, xref="x", yref="y", x=0, y=h, sizex=w, sizey=h, sizing="stretch", layer="below"))
            fig.update_xaxes(range=[0, w], visible=True)
            fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
        else:
            fig.update_xaxes(range=[0, 1000])
            fig.update_yaxes(range=[0, 1000], scaleanchor="x")
            st.info("Nessuna immagine. Griglia 1000x1000 attiva.")

        # Disegno punti
        if st.session_state.punti_manuali:
            df_p = pd.DataFrame(st.session_state.punti_manuali)
            fig.add_trace(go.Scatter(x=df_p['X'], y=df_p['Y'], mode='markers+text', text=df_p['Nome'],
                                     marker=dict(size=15, color='red', symbol='diamond'), textposition="top center"))
        
        fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

def modulo_grafici():
    st.header("📈 Grafici")
    if st.session_state.anagrafica is None:
        st.warning("⚠️ Carica un file Excel dalla sidebar per sbloccare i grafici.")
    else:
        st.success("Dati pronti per l'analisi.")

# --- 3. LOGICA PRINCIPALE (MAIN) ---

def main():
    st.sidebar.title("🛠️ DIMOS PANEL")
    scelta = st.sidebar.radio("Navigazione:", ["Home", "Mappe", "Grafici"])
    
    file_up = st.sidebar.file_uploader("📂 Excel", type=['xlsx', 'xlsm'])
    
    # Processo Excel solo se caricato
    if file_up:
        try:
            xls = pd.ExcelFile(file_up)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
                # Logica minima per non far crashare
                st.session_state.anagrafica = {"Caricato": True}
        except:
            pass

    # Esecuzione dei moduli in base alla scelta
    if scelta == "Home":
        st.title("Benvenuto")
    elif scelta == "Mappe":
        modulo_mappe()
    elif scelta == "Grafici":
        modulo_grafici()

if __name__ == "__main__":
    main()
