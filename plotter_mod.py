import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from docx import Document

# --- CONFIGURAZIONE E LOGO ---
st.set_page_config(layout="wide", page_title="DIMOS Monitoraggio")

# Logo largo 400px
try:
    st.image("logo_dimos.jpg", width=400)
except:
    st.write("### DIMOS SOFTWARE")

st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
st.divider()

# --- SIDEBAR (FILTRI TECNICI) ---
with st.sidebar:
    st.header("⚙️ Parametri Analisi")
    sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0, 0.1)
    rimuovi_zeri = st.checkbox("Elimina valori '0'", value=True)
    st.divider()
    st.info("Regola qui i filtri statistici. La selezione dei sensori è nella pagina principale.")

# --- FUNZIONI DI PULIZIA ---
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

# --- CARICAMENTO FILE (PAGINA PRINCIPALE) ---
uploaded_file = st.file_uploader("📂 Carica il file Excel (deve contenere i fogli 'NAME' e i dati)", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        gerarchia = {}
        # Caso EXCEL con fogli multipli
        if uploaded_file.name.endswith('.xlsx'):
            xls = pd.ExcelFile(uploaded_file)
            # Cerchiamo il foglio dei dati (es. 'flegrei')
            sheet_dati = [s for s in xls.sheet_names if s != "NAME"][0]
            df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
            
            if "NAME" in xls.sheet_names:
                df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
                # Costruzione gerarchia sicura
                for i, col_name in enumerate(df_dati.columns):
                    if i == 0: continue
                    try:
                        # Usiamo .iloc con gestione errore per evitare KeyError: 0
                        dl = str(df_name.iloc[0, i]).strip() if len(df_name) > 0 else "DL_Generico"
                        sens = str(df_name.iloc[1, i]).strip() if len(df_name) > 1 else "Sensore"
                    except:
                        dl, sens = "Generale", "Vari"
                    
                    if dl not in gerarchia: gerarchia[dl] = {}
                    if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                    gerarchia[dl][sens].append(col_name)
        else:
            # Caso CSV o Fallback
            df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')

        # Fallback se la gerarchia è vuota (Parsing dal nome colonna)
        if not gerarchia:
            for col in df_dati.columns[1:]:
                parts = col.split(' ')
                dl = parts[0].split('_')[0] + "_" + parts[0].split('_')[1] if '_' in parts[0] else parts[0]
                sens = parts[0]
                if dl not in gerarchia: gerarchia[dl] = {}
                if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                gerarchia[dl][sens].append(col)

        # Gestione Tempo
        col_t = df_dati.columns[0]
        df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
        df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)

        # --- SELEZIONE UI ---
        st.subheader("🔍 Selezione Dati")
        c1, c2 = st.columns(2)
        with c1:
            sel_dl = st.multiselect("Seleziona Centraline", options=sorted(list(gerarchia.keys())))
        with c2:
            sens_all = []
            for d in sel_dl: sens_all.extend(list(gerarchia[d].keys()))
            sel_sens = st.multiselect("Seleziona Sensori", options=sorted(list(set(sens_all))))

        # Filtro Date
        st.write("---")
        min_d, max_d = df_dati[col_t].min(), df_dati[col_t].max()
        d_col1, d_col2 = st.columns(2)
        with d_col1: start_dt = st.date_input("Inizio", min_d)
        with d_col2: end_dt = st.date_input("Fine", max_d)

        # --- GRAFICO ---
        cols_to_plot = []
        for d in sel_dl:
            for s in sel_sens:
                if s in gerarchia[d]: cols_to_plot.extend(gerarchia[d][s])

        if cols_to_plot:
            mask = (df_dati[col_t].dt.date >= start_dt) & (df_dati[col_t].dt.date <= end_dt)
            df_p = df_dati.loc[mask]
            
            fig = go.Figure()
            stats_list = []

            for c in cols_to_plot:
                y_pulita, diag = pulisci_dati(df_p[c], sigma_val, rimuovi_zeri)
                diag["Parametro"] = c
                stats_list.append(diag)
                fig.add_trace(go.Scatter(x=df_p[col_t], y=y_pulita, name=c))

            fig.update_layout(height=600, xaxis=dict(rangeslider=dict(visible=True)))
            st.plotly_chart(fig, use_container_width=True)

            # Report Gauss/Zeri
            st.subheader("📊 Report Analisi (Zeri e Gauss)")
            st.table(pd.DataFrame(stats_list).set_index("Parametro"))

            # Download Ascisse
            txt = df_p[col_t].dt.strftime('%d/%m/%Y %H:%M:%S').to_string(index=False)
            st.download_button("💾 Scarica Ascisse (TXT)", txt, "ascisse.txt")
            
        else:
            st.info("Seleziona una centralina e un sensore per visualizzare i dati.")

    except Exception as e:
        st.error(f"Errore durante l'elaborazione: {e}. Controlla che il foglio 'NAME' sia compilato correttamente.")

else:
    st.warning("Carica un file per iniziare.")
