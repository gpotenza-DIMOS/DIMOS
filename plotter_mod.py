import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from datetime import datetime

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
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
    st.divider()

    # --- SIDEBAR: PARAMETRI (Invariati) ---
    st.sidebar.header("⚙️ Parametri Modulo")
    sigma_val = st.sidebar.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
    rimuovi_zeri = st.sidebar.checkbox("Elimina letture a '0'", value=True)
    st.sidebar.divider()

    uploaded_file = st.file_uploader("📂 Carica file Excel (NAME + Dati) o CSV", type=['xlsx', 'xlsm', 'csv'])

    if uploaded_file:
        gerarchia = {}
        df_dati = pd.DataFrame()

        try:
            if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
                xls = pd.ExcelFile(uploaded_file)
                # Selezione automatica del foglio dati
                sheet_names = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]]
                if not sheet_names:
                    st.error("Nessun foglio dati trovato oltre a NAME/Info.")
                    return
                df_dati = pd.read_excel(xls, sheet_name=sheet_names[0])
                
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
                df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')

            # --- CORREZIONE DEFINITIVA DATE ---
            col_t = df_dati.columns[0]
            
            # Tentativo 1: Conversione standard (dayfirst per formato IT)
            df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
            
            # Tentativo 2: Se fallisce, forza il formato specifico spesso presente nei log (GG/MM/AAAA HH:MM:SS)
            if df_dati[col_t].isna().all():
                df_dati[col_t] = pd.to_datetime(df_dati[col_t], format='%d/%m/%Y %H:%M:%S', errors='coerce')

            # Rimuove righe dove la data è illeggibile
            df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)

            if not gerarchia:
                for col in df_dati.columns[1:]:
                    if "Centralina" not in gerarchia: gerarchia["Centralina"] = {}
                    gerarchia["Centralina"][col] = [col]

            # --- SELEZIONE UI ---
            st.subheader("🔍 Selezione Centraline e Sensori")
            c1, c2 = st.columns(2)
            with c1:
                sel_dl = st.multiselect("Seleziona Centraline", options=sorted(list(gerarchia.keys())))
            with c2:
                sens_opts = []
                for d in sel_dl: sens_opts.extend(list(gerarchia[d].keys()))
                sel_sens = st.multiselect("Seleziona Sensori", options=sorted(list(set(sens_opts))))

            # FILTRO TEMPORALE (Assicurati che min_d e max_d siano validi)
            st.write("---")
            min_d, max_d = df_dati[col_t].min().date(), df_dati[col_t].max().date()
            t1, t2 = st.columns(2)
            with t1: start_dt = st.date_input("Inizio Analisi", min_d, min_value=min_d, max_value=max_d)
            with t2: end_dt = st.date_input("Fine Analisi", max_d, min_value=min_d, max_value=max_d)

            # --- GENERAZIONE GRAFICO ---
            final_cols = []
            for d in sel_dl:
                for s in sel_sens:
                    if s in gerarchia[d]: final_cols.extend(gerarchia[d][s])

            if final_cols:
                # Filtraggio rigoroso tra le date selezionate
                mask = (df_dati[col_t].dt.date >= start_dt) & (df_dati[col_t].dt.date <= end_dt)
                df_p = df_dati.loc[mask].copy()
                
                if not df_p.empty:
                    fig = go.Figure()
                    for col in final_cols:
                        # Pulizia dati prima del plot
                        y_vals = pulisci_dati(df_p[col], sigma_val, rimuovi_zeri)
                        fig.add_trace(go.Scatter(
                            x=df_p[col_t], 
                            y=y_vals, 
                            name=str(col), 
                            mode='lines+markers',
                            connectgaps=False # Evita linee rette tra dati mancanti
                        ))
                    
                    fig.update_layout(
                        height=600, 
                        template="plotly_white",
                        xaxis=dict(title="Data e Ora", rangeslider=dict(visible=True)),
                        yaxis=dict(title="Valore"),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"Nessun dato trovato tra il {start_dt} e il {end_dt}. Verifica l'intervallo.")
            else:
                st.info("Seleziona almeno una centralina e un sensore per visualizzare il grafico.")

        except Exception as e:
            st.error(f"Errore tecnico nel modulo Plotter: {e}")

if __name__ == "__main__":
    run_plotter()
