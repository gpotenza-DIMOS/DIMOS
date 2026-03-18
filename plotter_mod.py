import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(layout="wide", page_title="Monitoraggio Avanzato Flegrei")

# --- LOGICA DI PARSING DEI METADATI ---
def parse_metadata(df_data, df_name=None):
    """
    Crea un dizionario gerarchico dei sensori.
    Struttura: { 'Datalogger': { 'Sensore': [Lista Colonne] } }
    """
    mapping = {}
    
    for col in df_data.columns:
        if col == "Data e Ora": continue
        
        # Caso A: Esiste il file NAME con 3 righe (Datalogger, Sensore, Parametro)
        if df_name is not None and col in df_name.columns:
            logger = str(df_name.at[0, col])
            sensore = str(df_name.at[1, col])
        else:
            # Caso B: Parsing manuale (Esempio: CO_9286 BATT [V])
            parts = col.split(' ')
            logger = parts[0] if len(parts) > 0 else "Unknown"
            # Se c'è un codice tipo CL_01, lo usiamo come sensore, altrimenti il parametro
            sensore = parts[1] if len(parts) > 1 else "Gen_Sens"
        
        if logger not in mapping: mapping[logger] = {}
        if sensore not in mapping[logger]: mapping[logger][sensore] = []
        mapping[logger][sensore].append(col)
            
    return mapping

# --- LOGICA FILTRI (GAUSS & ZERI) ---
def applica_filtri_statistici(serie, n_sigma, rimuovi_zeri):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    
    if rimuovi_zeri:
        diag["zeri"] = (originale == 0).sum()
        originale = originale.replace(0, np.nan)
    
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        mean, std = validi.mean(), validi.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diag["gauss"] = outliers.sum()
            originale[outliers] = np.nan
            
    return originale, diag

# --- INTERFACCIA ---
st.title("🛰️ Analisi Gerarchica Datalogger")

# Sidebar: Solo parametri di calcolo
with st.sidebar:
    st.header("⚙️ Parametri Analisi")
    sigma = st.slider("Soglia Outlier (Sigma Gauss)", 0.0, 5.0, 3.0, 0.5)
    rimuovi_zeri = st.checkbox("Rimuovi Zeri (Errori lettura)", value=True)
    st.divider()
    st.info("I filtri di selezione dati sono ora nella pagina principale.")

# Caricamento file
uploaded_data = st.file_uploader("Carica file Dati (CSV)", type="csv")
uploaded_name = st.file_uploader("Carica file NAME (Opzionale)", type="csv")

if uploaded_data:
    df = pd.read_csv(uploaded_data, sep=None, engine='python')
    df_n = pd.read_csv(uploaded_name, sep=None, engine='python', header=None) if uploaded_name else None
    
    # 1. Parsing dei metadati
    struttura = parse_metadata(df, df_n)
    
    # 2. Selezione Dati nella Pagina Principale
    st.subheader("🔍 Selezione Datalogger e Sensori")
    c1, c2 = st.columns(2)
    
    with c1:
        loggers_sel = st.multiselect("Seleziona Centraline/Datalogger", options=list(struttura.keys()))
    
    with c2:
        sensori_disponibili = []
        for l in loggers_sel:
            sensori_disponibili.extend(list(struttura[l].keys()))
        sensori_sel = st.multiselect("Seleziona Sensori", options=list(set(sensori_disponibili)))

    # Esplosione delle colonne finali da graficare
    colonne_finali = []
    for l in loggers_sel:
        for s in sensori_sel:
            if s in struttura[l]:
                colonne_finali.extend(struttura[l][s])

    if colonne_finali:
        # 3. Preparazione Dati e Grafico
        fig = go.Figure()
        stats_report = {}

        for col in colonne_finali:
            serie_pulita, diag = applica_filtri_statistici(df[col], sigma, rimuovi_zeri)
            stats_report[col] = diag
            
            fig.add_trace(go.Scatter(
                x=df["Data e Ora"], 
                y=serie_pulita, 
                name=col,
                mode='lines+markers',
                marker=dict(size=4)
            ))

        # Configurazione Ascisse (Dinamiche)
        fig.update_layout(
            xaxis_title="Timeline",
            template="plotly_white",
            height=700,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )

        st.plotly_chart(fig, use_container_width=True)

        # 4. Diagnostica e Esportazione
        with st.expander("📊 Report Qualità Dati (Gauss & Zeri)"):
            st.table(pd.DataFrame(stats_report).T)

        st.download_button(
            "💾 Esporta pulizia (CSV)",
            df[["Data e Ora"] + colonne_finali].to_csv(index=False).encode('utf-8'),
            "dati_filtrati.csv",
            "text/csv"
        )
    else:
        st.warning("Seleziona almeno una centralina e un sensore per visualizzare il grafico.")

else:
    st.info("Inizia caricando il file dei dati.")
