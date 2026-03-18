import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAZIONE E LOGO ---
st.set_page_config(layout="wide", page_title="DIMOS Monitoraggio")

# Layout superiore: Logo e Titolo
col_l, col_t = st.columns([1, 5])
with col_l:
    try:
        st.image("logo_dimos.jpg", width=120)
    except:
        st.write("Logo DIMOS")

with col_t:
    st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")

st.divider()

# --- SIDEBAR: SOLO PARAMETRI TECNICI ---
with st.sidebar:
    st.header("⚙️ Parametri Analisi")
    sigma_val = st.slider("Filtro Gauss (Sigma)", 0.1, 5.0, 3.0, 0.1)
    rimuovi_zeri = st.checkbox("Elimina valori '0'", value=True)
    st.divider()
    uploaded_data = st.file_uploader("1. Carica File Dati (CSV/XLSX)", type=['csv', 'xlsx'])
    uploaded_name = st.file_uploader("2. Carica File NAME (Opzionale)", type=['csv'])

# --- FUNZIONI DI ELABORAZIONE ---
def clean_data(serie, sigma, drop_zeros):
    diag = {'zeri': 0, 'gauss': 0}
    temp_serie = serie.copy()
    if drop_zeros:
        diag['zeri'] = (temp_serie == 0).sum()
        temp_serie = temp_serie.replace(0, np.nan)
    
    if sigma > 0:
        m, s = temp_serie.mean(), temp_serie.std()
        outliers = (temp_serie < m - sigma*s) | (temp_serie > m + sigma*s)
        diag['gauss'] = outliers.sum()
        temp_serie[outliers] = np.nan
    return temp_serie, diag

# --- LOGICA PRINCIPALE ---
if uploaded_data:
    # Caricamento dati
    df = pd.read_csv(uploaded_data, sep=None, engine='python')
    
    # Trova colonna Data (evita KeyError)
    col_data = df.columns[0]
    for c in df.columns:
        if 'data' in c.lower() or 'ora' in c.lower() or 'time' in c.lower():
            col_data = c
            break
    
    df[col_data] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[col_data]).sort_values(col_data)

    # Parsing Gerarchia (Centralina -> Sensore -> Parametri)
    struttura = {}
    
    if uploaded_name:
        df_n = pd.read_csv(uploaded_name, header=None, sep=None, engine='python')
        # Logica: riga 0=logger, riga 1=sensore, riga 2=parametro
        for i, col_name in enumerate(df.columns):
            if col_name == col_data: continue
            try:
                log = str(df_n.iloc[0, i])
                sens = str(df_n.iloc[1, i])
            except:
                log, sens = "Generale", "Vari"
            
            if log not in struttura: struttura[log] = {}
            if sens not in struttura[log]: struttura[log][sens] = []
            struttura[log][sens].append(col_name)
    else:
        # Fallback se manca NAME
        for col_name in df.columns:
            if col_name == col_data: continue
            log = col_name.split('_')[0] if '_' in col_name else "Generale"
            sens = col_name.split(' ')[1] if len(col_name.split(' ')) > 1 else "Sensore"
            if log not in struttura: struttura[log] = {}
            if sens not in struttura[log]: struttura[log][sens] = []
            struttura[log][sens].append(col_name)

    # --- UI DI SELEZIONE NELLA PAGINA PRINCIPALE ---
    st.subheader("🔍 Filtro Centralina e Sensori")
    c1, c2 = st.columns(2)
    
    with c1:
        loggers_sel = st.multiselect("Seleziona Centraline", options=sorted(list(struttura.keys())))
    
    with c2:
        sens_opt = []
        for l in loggers_sel:
            sens_opt.extend(list(struttura[l].keys()))
        sens_sel = st.multiselect("Seleziona Sensori", options=sorted(list(set(sens_opt))))

    # Filtro Date Manuale (come richiesto)
    st.write("---")
    min_date, max_date = df[col_data].min(), df[col_data].max()
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        start_d = st.date_input("Data Inizio", min_date)
    with d_col2:
        end_d = st.date_input("Data Fine", max_date)

    # Filtraggio DataFrame finale
    mask = (df[col_data].dt.date >= start_d) & (df[col_data].dt.date <= end_d)
    df_plot = df.loc[mask]

    # --- GRAFICO E REPORT ---
    col_finali = []
    for l in loggers_sel:
        for s in sens_sel:
            if s in struttura[l]:
                col_finali.extend(struttura[l][s])

    if col_finali:
        fig = go.Figure()
        stats_list = []

        for c in col_finali:
            y_clean, d_info = clean_data(df_plot[c], sigma_val, rimuovi_zeri)
            d_info['Parametro'] = c
            stats_list.append(d_info)
            
            fig.add_trace(go.Scatter(x=df_plot[col_data], y=y_clean, name=c, mode='lines'))

        fig.update_layout(
            height=600,
            xaxis=dict(rangeslider=dict(visible=True), type="date"),
            hovermode="x unified",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabella Analisi Gauss/Zeri
        st.subheader("📋 Report Qualità Dati")
        st.table(pd.DataFrame(stats_list).set_index('Parametro'))
        
        # Bottoni stampa/export
        st.download_button("📩 Scarica Dati Filtrati (CSV)", df_plot[col_finali].to_csv().encode('utf-8'), "dati.csv")
    else:
        st.info("Seleziona una centralina e un sensore per generare il grafico.")

else:
    st.warning("In attesa del caricamento dei file dati...")
