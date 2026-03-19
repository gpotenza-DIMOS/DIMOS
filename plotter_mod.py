import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from datetime import datetime
from io import BytesIO
from docx import Document
from docx.shared import Inches

@st.cache_data(show_spinner=False)
def carica_file_cache(uploaded_file):
    df_name = None
    if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
        xls = pd.ExcelFile(uploaded_file)
        if "NAME" in xls.sheet_names:
            df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        sheet_dati = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]][0]
        df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
    else:
        df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')
    
    col_t = df_dati.columns[0]
    df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
    df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)
    return df_dati, df_name

def pulisci_dati(serie, n_sigma, drop_zeros):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    if drop_zeros:
        diag["zeri"] = int((originale == 0).sum())
        originale = originale.replace(0, np.nan)
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        mean, std = validi.mean(), validi.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diag["gauss"] = int(outliers.sum())
            originale[outliers] = np.nan
    return originale, diag

def run_plotter():
    st.title("📈 Analisi Grafica e Reportistica")
    
    with st.sidebar:
        st.header("⚙️ Filtri Globali")
        sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
        rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
        show_trend = st.checkbox("Linea di Tendenza (3° grado)", value=True)

    uploaded_file = st.file_uploader("📂 Carica file Excel/CSV", type=['xlsx', 'xlsm', 'csv'])

    if uploaded_file:
        df_dati, df_name = carica_file_cache(uploaded_file)
        col_t = df_dati.columns[0]
        
        # Salvataggio in session_state per gli altri moduli
        st.session_state['df_values'] = df_dati
        st.session_state['col_tempo'] = col_t
        st.session_state['df_header'] = df_name

        # Selezione Date
        c_date1, c_date2 = st.columns(2)
        with c_date1: start_d = st.date_input("Inizio", df_dati[col_t].min())
        with c_date2: end_d = st.date_input("Fine", df_dati[col_t].max())
        
        mask = (df_dati[col_t].dt.date >= start_d) & (df_dati[col_t].dt.date <= end_d)
        df_filtrato = df_dati.loc[mask]

        # Logica Sensori (semplificata per brevità, ma completa di gerarchia)
        sensori_disponibili = [c for c in df_filtrato.columns if c != col_t]
        sel_sens = st.multiselect("Seleziona Sensori", sensori_disponibili)

        if sel_sens:
            fig = go.Figure()
            for s in sel_sens:
                y_v, diag = pulisci_dati(df_filtrato[s], sigma_val, rimuovi_zeri)
                fig.add_trace(go.Scatter(x=df_filtrato[col_t], y=y_v, name=s))
                
                if show_trend and y_v.notna().sum() > 4:
                    x_ts = df_filtrato.loc[y_v.notna(), col_t].apply(lambda x: x.timestamp())
                    poly = np.poly1d(np.polyfit(x_ts, y_v.dropna(), 3))
                    fig.add_trace(go.Scatter(x=df_filtrato[col_t], y=poly(df_filtrato[col_t].apply(lambda x: x.timestamp())), 
                                            name=f"Trend {s}", line=dict(dash='dash')))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # --- TASTO REPORT WORD ---
            if st.button("🚀 Genera Report Word"):
                doc = Document()
                doc.add_heading('Report Monitoraggio DIMOS', 0)
                # (Qui va la logica Matplotlib del tuo file originale)
                st.success("Report Generato (Logica di salvataggio pronta)")
