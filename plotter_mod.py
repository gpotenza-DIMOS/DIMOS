import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
from datetime import datetime

# --- LOGICA FILTRI ---
def applica_filtri_completi(serie, n_sigma, rimuovi_zeri):
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

# --- CARICAMENTO DATI (CSV SEPARATI) ---
def load_data(file_name_csv, file_data_csv):
    # Legge i metadati (NAME) - 3 righe
    df_name = pd.read_csv(file_name_csv, sep=';', header=None, nrows=3)
    
    # Legge i dati (flegrei)
    df_values = pd.read_csv(file_data_csv, sep=';')
    
    # Pulizia colonne
    df_values.columns = [str(c).strip() for c in df_values.columns]
    col_tempo = df_values.columns[0]
    df_values[col_tempo] = pd.to_datetime(df_values[col_tempo], errors='coerce')
    df_values = df_values.dropna(subset=[col_tempo]).sort_values(by=col_tempo)
    
    return df_name, df_values, col_tempo

def run_plotter():
    st.header("📉 PLOTTER PRO - Analisi Sensori Multi-Canale")
    
    with st.sidebar:
        st.header("📂 Caricamento File")
        f_name = st.file_uploader("Carica file NAME (Metadati)", type=['csv'])
        f_data = st.file_uploader("Carica file DATI (flegrei)", type=['csv'])
        st.divider()
        tipo_asse_x = st.radio("Asse X:", ["Temporale", "Sequenziale"])
        passo_date = st.number_input("Etichette ogni N date:", value=100, min_value=1)
        rimuovi_zeri = st.toggle("Rimuovi Zeri Puri", value=True)
        usa_gauss = st.checkbox("Attiva Gauss", value=True)
        sigma = st.slider("Sigma", 0.5, 5.0, 2.0) if usa_gauss else 0

    if not f_name or not f_data:
        return st.info("Carica entrambi i file CSV per procedere.")

    try:
        df_header, df_values, col_tempo = load_data(f_name, f_data)
        
        # --- MAPPATURA INTELLIGENTE ---
        # Organizziamo per Tipo -> Sensore -> Canale
        mappa = {}
        for col_idx in range(1, len(df_header.columns)):
            logger = str(df_header.iloc[0, col_idx])
            sensore = str(df_header.iloc[1, col_idx])
            canale_id = str(df_header.iloc[2, col_idx])
            
            # Identificazione Tipo
            if "[°]" in canale_id: t = "Inclinazione (°)"
            elif "°C" in canale_id: t = "Temperatura (°C)"
            elif "[m]" in canale_id: t = "Distanza (m)"
            elif "[V]" in canale_id: t = "Batteria (Volt)"
            else: t = "Diagnostica/Altro"
            
            if t not in mappa: mappa[t] = {}
            if sensore not in mappa[t]: mappa[t][sensore] = []
            mappa[t][sensore].append(canale_id)

        # --- UI SELEZIONE ---
        st.write("### 🛠️ Selezione Parametri")
        tipologie = st.multiselect("Quali grandezze vuoi analizzare?", sorted(mappa.keys()))
        
        targets = {} # { Tipo: [Lista canali ID] }
        if tipologie:
            cols = st.columns(len(tipologie))
            for i, t in enumerate(tipologie):
                with cols[i]:
                    sensori_scelti = st.multiselect(f"Sensori {t}:", list(mappa[t].keys()))
                    if sensori_scelti:
                        targets[t] = []
                        for s in sensori_scelti:
                            targets[t].extend(mappa[t][s])

        if targets:
            st.divider()
            # Filtro temporale
            start = st.date_input("Inizio:", df_values[col_tempo].min().date())
            end = st.date_input("Fine:", df_values[col_tempo].max().date())
            
            df_p = df_values[(df_values[col_tempo].dt.date >= start) & 
                             (df_values[col_tempo].dt.date <= end)].copy().reset_index(drop=True)

            # CREAZIONE SUBPLOTS
            n_rows = len(targets)
            fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.07, subplot_titles=list(targets.keys()))
            
            stats_final = {}
            for row_idx, (tipo, canali) in enumerate(targets.items(), 1):
                for c_id in canali:
                    y_clean, diag = applica_filtri_completi(df_p[c_id], sigma, rimuovi_zeri)
                    label_clean = c_id.split(" ")[-2:] # Accorcia l'etichetta
                    stats_final[c_id] = diag
                    
                    temp_df = pd.DataFrame({'x': df_p.index if tipo_asse_x == "Sequenziale" else df_p[col_tempo], 'y': y_clean}).dropna()
                    
                    fig.add_trace(go.Scatter(x=temp_df['x'], y=temp_df['y'], name=c_id, mode='lines+markers'), row=row_idx, col=1)

            # Layout
            fig.update_layout(height=400 * n_rows, template="plotly_white", hovermode="x unified")
            if tipo_asse_x == "Sequenziale":
                ticks = [df_p.iloc[i][col_tempo].strftime('%d/%m %H:%M') if i % passo_date == 0 else "" for i in range(len(df_p))]
                fig.update_layout(xaxis=dict(tickmode='array', tickvals=list(df_p.index), ticktext=ticks))

            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📋 Diagnostica"):
                st.table(pd.DataFrame(stats_final).T)

    except Exception as e:
        st.error(f"Errore durante l'elaborazione: {e}")

if __name__ == "__main__":
    run_plotter()
