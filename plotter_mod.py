import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO

# --- GESTIONE LIBRERIA WORD ---
try:
    from docx import Document
    WORD_OK = True
except ImportError:
    WORD_OK = False

def pulisci_dati(serie, n_sigma, drop_zeros):
    """Analisi di Gauss e rimozione zeri."""
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
    # --- HEADER ---
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
    st.divider()

    # --- SIDEBAR (PARAMETRI TECNICI) ---
    with st.sidebar:
        st.header("⚙️ Impostazioni Analisi")
        sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0, 0.1)
        rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
        st.divider()

    # --- CARICAMENTO FILE ---
    uploaded_file = st.file_uploader("📂 Carica file Excel (NAME + Dati) o CSV", type=['xlsx', 'csv'])

    if uploaded_file:
        gerarchia = {}
        df_dati = pd.DataFrame()

        try:
            if uploaded_file.name.endswith('.xlsx'):
                xls = pd.ExcelFile(uploaded_file)
                sheet_dati = [s for s in xls.sheet_names if s != "NAME"][0]
                df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
                
                if "NAME" in xls.sheet_names:
                    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
                    for i, col_name in enumerate(df_dati.columns):
                        if i == 0: continue 
                        try:
                            dl = str(df_name.iloc[0, i]).strip() if len(df_name) > 0 else "DL_Generico"
                            sens = str(df_name.iloc[1, i]).strip() if len(df_name) > 1 else "Sensore"
                        except:
                            dl, sens = "Generale", "Vari"
                        
                        if dl not in gerarchia: gerarchia[dl] = {}
                        if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                        gerarchia[dl][sens].append(col_name)
            else:
                # Migliorata lettura CSV
                df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')

            # --- GESTIONE TEMPO (Punto Critico) ---
            col_t = df_dati.columns[0]
            # Prova diversi formati comuni se la conversione standard fallisce
            df_dati[col_t] = pd.to_datetime(df_dati[col_t], errors='coerce')
            
            # Se la conversione fallisce, prova a forzare il formato italiano tipico dei CSV
            if df_dati[col_t].isnull().all():
                df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')

            df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)

            if df_dati.empty:
                st.error("Errore: Impossibile interpretare le date nella prima colonna.")
                return

            # --- FALLBACK GERARCHIA ---
            if not gerarchia:
                for col in df_dati.columns[1:]:
                    parts = str(col).split('_')
                    dl = parts[0] if len(parts) > 0 else "Dati"
                    sens = col
                    if dl not in gerarchia: gerarchia[dl] = {}
                    if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                    gerarchia[dl][sens].append(col)

            # --- SELEZIONE UI ---
            st.subheader("🔍 Selezione Centraline e Sensori")
            c1, c2 = st.columns(2)
            with c1:
                sel_dl = st.multiselect("Seleziona Centraline", options=sorted(list(gerarchia.keys())))
            with c2:
                sens_opts = []
                for d in sel_dl: sens_opts.extend(list(gerarchia[d].keys()))
                sel_sens = st.multiselect("Seleziona Sensori", options=sorted(list(set(sens_opts))))

            # --- FILTRO TEMPORALE ---
            st.write("---")
            min_d, max_d = df_dati[col_t].min().date(), df_dati[col_t].max().date()
            t1, t2 = st.columns(2)
            with t1: start_dt = st.date_input("Inizio Analisi", min_d)
            with t2: end_dt = st.date_input("Fine Analisi", max_d)

            # --- ELABORAZIONE GRAFICO ---
            final_cols = []
            for d in sel_dl:
                for s in sel_sens:
                    if s in gerarchia[d]: final_cols.extend(gerarchia[d][s])

            if final_cols:
                mask = (df_dati[col_t].dt.date >= start_dt) & (df_dati[col_t].dt.date <= end_dt)
                df_p = df_dati.loc[mask]
                
                if df_p.empty:
                    st.warning("Nessun dato presente nell'intervallo temporale selezionato.")
                else:
                    fig = go.Figure()
                    report_stats = []

                    for col in final_cols:
                        y_clean, diag = pulisci_dati(df_p[col], sigma_val, rimuovi_zeri)
                        diag["Parametro"] = col
                        report_stats.append(diag)
                        fig.add_trace(go.Scatter(x=df_p[col_t], y=y_clean, name=col, mode='lines+markers'))

                    fig.update_layout(
                        height=600, template="plotly_white",
                        xaxis=dict(rangeslider=dict(visible=True), type="date"),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("📊 Report Analisi (Zeri e Gauss)")
                    st.table(pd.DataFrame(report_stats).set_index("Parametro"))

        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")

if __name__ == "__main__":
    import os
    run_plotter()
