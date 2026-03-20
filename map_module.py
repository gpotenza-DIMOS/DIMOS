import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import os

# --- 1. CONFIGURAZIONE E SESSION STATE ---
st.set_page_config(layout="wide", page_title="DIMOS - Sistema Integrato")

if 'sensori_manuali' not in st.session_state:
    st.session_state.sensori_manuali = []
if 'anagrafica' not in st.session_state:
    st.session_state.anagrafica = None
if 'df_dati' not in st.session_state:
    st.session_state.df_dati = None

# --- 2. LOGICA DI CARICAMENTO EXCEL ---
def carica_dati(file):
    try:
        xls = pd.ExcelFile(file)
        # Lettura Anagrafica (NAME)
        if "NAME" in xls.sheet_names:
            df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("")
            ana = {}
            for c in range(1, df_n.shape[1]):
                dl = str(df_n.iloc[0, c]).strip()
                sn = str(df_n.iloc[1, c]).strip()
                wb = str(df_n.iloc[2, c]).strip()
                if dl and dl != "nan":
                    if dl not in ana: ana[dl] = {}
                    ana[dl][sn] = wb
            st.session_state.anagrafica = ana
        
        # Lettura Dati (Terzo foglio o flegrei)
        sheet_dati = xls.sheet_names[2] 
        df = pd.read_excel(xls, sheet_name=sheet_dati)
        df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])
        st.session_state.df_dati = df
        return True
    except Exception as e:
        st.sidebar.error(f"Errore caricamento: {e}")
        return False

# --- 3. MODULO MAPPE (IL TUO NUOVO MODULO) ---
def modulo_mappe():
    st.header("🗺️ Mappe e Posizionamento CAD")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("📍 Inserimento Manuale")
        nome = st.text_input("Nome Sensore", value="Pippo")
        x = st.number_input("Coordinata X", value=0)
        y = st.number_input("Coordinata Y", value=0)
        
        if st.button("Posiziona Marker"):
            st.session_state.sensori_manuali.append({'Nome': nome, 'X': x, 'Y': y})
            st.rerun()
        
        if st.button("🗑️ Reset Mappa"):
            st.session_state.sensori_manuali = []
            st.rerun()
            
        st.divider()
        img_file = st.file_uploader("🖼️ Carica Sfondo (CAD/Mappa)", type=['png', 'jpg', 'jpeg'])

    with col2:
        fig = go.Figure()
        if img_file:
            img = Image.open(img_file)
            w, h = img.size
            fig.add_layout_image(dict(source=img, xref="x", yref="y", x=0, y=h, sizex=w, sizey=h, sizing="stretch", layer="below"))
            fig.update_xaxes(range=[0, w], visible=True)
            fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
        else:
            fig.update_xaxes(range=[0, 1000], title="X")
            fig.update_yaxes(range=[0, 1000], title="Y", scaleanchor="x")
        
        if st.session_state.sensori_manuali:
            df_p = pd.DataFrame(st.session_state.sensori_manuali)
            fig.add_trace(go.Scatter(x=df_p['X'], y=df_p['Y'], mode='markers+text', text=df_p['Nome'],
                                     marker=dict(size=15, color='red', symbol='diamond'), textposition="top center"))
        
        fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- 4. MODULO GRAFICI (IL TUO MODULO ORIGINALE) ---
def modulo_grafici():
    st.header("📈 Analisi Dati Monitoraggio")
    if st.session_state.anagrafica is None or st.session_state.df_dati is None:
        st.warning("⚠️ Carica il file Excel dalla sidebar per visualizzare i grafici.")
        return

    ana = st.session_state.anagrafica
    df = st.session_state.df_dati
    
    c1, c2 = st.columns(2)
    with c1:
        sel_dl = st.multiselect("Datalogger", sorted(ana.keys()))
    
    sensori_disp = [f"{d} | {s}" for d in sel_dl for s in ana[d].keys()]
    with c2:
        sel_sens = st.multiselect("Sensori", sensori_disp)
    
    if sel_sens:
        st.success(f"Visualizzazione di {len(sel_sens)} sensori...")
        # Qui segue la tua logica Plotly per i grafici (Trend, Gauss ecc.)

# --- 5. MAIN APP ---
def main():
    st.sidebar.title("🛠️ DIMOS CONTROL PANEL")
    scelta = st.sidebar.radio("Vai a:", ["Home", "Mappe", "Grafici"])
    
    file_up = st.sidebar.file_uploader("📂 Carica Excel", type=['xlsx', 'xlsm'])
    if file_up:
        carica_dati(file_up)

    if scelta == "Home":
        st.title("🏠 Benvenuto in DIMOS")
        st.write("Usa il menu a sinistra per navigare tra le mappe e i grafici.")
    elif scelta == "Mappe":
        modulo_mappe()
    elif scelta == "Grafici":
        modulo_grafici()

if __name__ == "__main__":
    main()
