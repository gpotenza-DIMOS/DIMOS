import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- MOTORE DI PULIZIA DATI (Invariato) ---
def pulisci_dati(serie, n_sigma, drop_zeros):
    originale = serie.copy()
    if drop_zeros:
        originale = originale.replace(0, np.nan)
    
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        mean, std = validi.mean(), validi.std()
        lower, upper = mean - n_sigma * std, mean + n_sigma * std
        originale[(originale < lower) | (originale > upper)] = np.nan
    return originale

def run_plotter():
    # Mantiene lo stile originale dell'header
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
    st.divider()

    # --- SIDEBAR: PARAMETRI DA SETTARE (Invariati) ---
    st.sidebar.header("⚙️ Parametri Modulo")
    sigma_val = st.sidebar.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
    rimuovi_zeri = st.sidebar.checkbox("Elimina letture a '0'", value=True)
    st.sidebar.divider()

    # --- CARICAMENTO E LOGICA DATI ---
    uploaded_file = st.file_uploader("📂 Carica file Excel (NAME + Dati) o CSV", type=['xlsx', 'xlsm', 'csv'])

    if uploaded_file:
        gerarchia = {}
        df_dati = pd.DataFrame()

        try:
            if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
                xls = pd.ExcelFile(uploaded_file)
                # Cerca il foglio dati (quello che non è NAME o Info)
                sheet_dati = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]][0]
                df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
                
                # Legge la gerarchia dal foglio NAME se esiste
                if "NAME" in xls.sheet_names:
                    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
                    for i, col_name in enumerate(df_dati.columns):
                        if i == 0: continue
                        try:
                            dl = str(df_name.iloc[0, i]).strip()
                            sens = str(df_name.iloc[1, i]).strip()
                        except:
                            dl, sens = "Generale", "Vari"
                        
                        if dl not in gerarchia: gerarchia[dl] = {}
                        if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                        gerarchia[dl][sens].append(col_name)
            else:
                # Gestione robusta per CSV (auto-detect separatore)
                df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')

            # --- CORREZIONE CRITICA: GESTIONE DATE ---
            col_t = df_dati.columns[0]
            # Prova a convertire con formato europeo (giorno prima) se standard fallisce
            df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
            df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)

            # Se dopo il caricamento CSV non c'è gerarchia, la crea dalle colonne
            if not gerarchia:
                for col in df_dati.columns[1:]:
                    dl = "Centralina"
                    if dl not in gerarchia: gerarchia[dl] = {}
                    gerarchia[dl][col] = [col]

            # --- OPZIONI GRAFICI E SENSORI (Invariate) ---
            st.subheader("🔍 Selezione Centraline e Sensori")
            c1, c2 = st.columns(2)
            with c1:
                sel_dl = st.multiselect("Seleziona Centraline", options=sorted(list(gerarchia.keys())))
            with c2:
                sens_opts = []
                for d in sel_dl:
                    sens_opts.extend(list(gerarchia[d].keys()))
                sel_sens = st.multiselect("Seleziona Sensori", options=sorted(list(set(sens_opts))))

            # Filtro temporale
            st.write("---")
            min_d, max_d = df_dati[col_t].min().date(), df_dati[col_t].max().date()
            t1, t2 = st.columns(2)
            with t1: start_dt = st.date_input("Inizio Analisi", min_d)
            with t2: end_dt = st.date_input("Fine Analisi", max_d)

            # --- VISUALIZZAZIONE (Invariata) ---
            final_cols = []
            for d in sel_dl:
                for s in sel_sens:
                    if s in gerarchia[d]:
                        final_cols.extend(gerarchia[d][s])

            if final_cols:
                mask = (df_dati[col_t].dt.date >= start_dt) & (df_dati[col_t].dt.date <= end_dt)
                df_p = df_dati.loc[mask]
                
                if not df_p.empty:
                    fig = go.Figure()
                    for col in final_cols:
                        y_plot = pulisci_dati(df_p[col], sigma_val, rimuovi_zeri)
                        fig.add_trace(go.Scatter(x=df_p[col_t], y=y_plot, name=col, mode='lines+markers'))
                    
                    fig.update_layout(
                        height=600, template="plotly_white",
                        xaxis=dict(rangeslider=dict(visible=True)),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Nessun dato nell'intervallo temporale selezionato.")

        except Exception as e:
            st.error(f"Errore nel caricamento dati: {e}")
