import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from docx import Document

def pulisci_dati(serie, n_sigma, drop_zeros):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    if drop_zeros:
        diag["zeri"] = int((originale == 0).sum())
        originale = originale.replace(0, np.nan)
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        m, s = validi.mean(), validi.std()
        mask = (originale < m - n_sigma*s) | (originale > m + n_sigma*s)
        diag["gauss"] = int(mask.sum())
        originale[mask] = np.nan
    return originale, diag

def run_plotter():
    st.title("📈 Monitoraggio - Visualizzazione e Stampe")
    
    # Parametri in colonna laterale o in alto
    with st.expander("⚙️ Impostazioni Analisi Statistici", expanded=False):
        c1, c2 = st.columns(2)
        sigma_val = c1.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0, 0.1)
        rimuovi_zeri = c2.checkbox("Elimina valori '0'", value=True)

    uploaded_file = st.file_uploader("Carica Excel Monitoraggio", type=["xlsx"])

    if uploaded_file:
        df_dati = pd.read_excel(uploaded_file)
        col_t = df_dati.columns[0]
        df_dati[col_t] = pd.to_datetime(df_dati[col_t])
        
        # Logica di gerarchia sensori
        cols = df_dati.columns[1:]
        gerarchia = {}
        for c in cols:
            parti = str(c).split("_")
            dl = parti[0]
            sensore = "_".join(parti[:2])
            if dl not in gerarchia: gerarchia[dl] = {}
            if sensore not in gerarchia[dl]: gerarchia[dl][sensore] = []
            gerarchia[dl][sensore].append(c)

        col1, col2 = st.columns(2)
        with col1:
            sel_dl = st.multiselect("Datalogger", list
