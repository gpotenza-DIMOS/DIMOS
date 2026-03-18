import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Monitoraggio", layout="wide")

# --- HEADER: LOGO E TITOLO ---
col_logo, col_titolo = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_dimos.jpg", width=150)
    except:
        st.warning("Logo non trovato (caricare logo_dimos.jpg)")

st.markdown("## Dati Monitoraggio - Visualizzazione e stampa")
st.write("---")

# --- LOGICA FILTRI ---
def applica_filtri(serie, n_sigma, rimuovi_zeri):
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

# --- CARICAMENTO E PARSING DATI ---
uploaded_file = st.sidebar.file_uploader("Carica file CSV o Excel", type=['csv', 'xlsx'])

if uploaded_file:
    # Caricamento (tentativo con separatore ; o ,)
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df_raw = pd.read_excel(uploaded_file)
            
        # Rilevazione struttura NAME (3 righe header) o Standard (1 riga header)
        # Assumiamo che la prima colonna sia sempre "Data e Ora"
        
        st.sidebar.header("⚙️ Impostazioni Analisi e Filtri")
        rimuovi_zeri = st.sidebar.checkbox("Rimuovi Zeri (0)", value=True)
        sigma = st.sidebar.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0, 0.1)

        # Pulizia Nomi Colonne e Mapping Gerarchico
        # Se le prime righe contengono info centralina/sensore, le usiamo
        cols = df_raw.columns.tolist()
        mapping = {}
        
        for col in cols[1:]: # Escludiamo Data e Ora
            parts = col.split()
            # Esempio: CO_9286 BATT [V]
            centralina = parts[0] if "_" in parts[0] else "Generale"
            parametro = col
            mapping[col] = f"{centralina} >> {parametro}"

        # Selezione Centralina/Sensore
        opzioni = list(mapping.values())
        scelte = st.sidebar.multiselect("Seleziona Grandezze da visualizzare:", opzioni)

        if scelte:
            # Conversione data
            df_raw[cols[0]] = pd.to_datetime(df_raw[cols[0]], dayfirst=True, errors='coerce')
            df_raw = df_raw.dropna(subset=[cols[0]]).sort_values(cols[0])
            
            # Filtro Date
            min_d, max_d = df_raw[cols[0]].min(), df_raw[cols[0]].max()
            start_date = st.sidebar.date_input("Inizio", min_d)
            end_date = st.sidebar.date_input("Fine", max_d)
            
            mask = (df_raw[cols[0]].dt.date >= start_date) & (df_raw[cols[0]].dt.date <= end_date)
            df_p = df_raw.loc[mask].copy()
            
            # Grafico e Analisi
            fig = go.Figure()
            stats_final = []

            for scelta in scelte:
                # Trova la colonna originale dal mapping
                col_orig = [k for k, v in mapping.items() if v == scelta][0]
                
                # Applica Filtri
                serie_filtrata, diag = applica_filtri(df_p[col_orig], sigma, rimuovi_zeri)
                
                # Aggiungi al grafico
                fig.add_trace(go.Scatter(
                    x=df_p[cols[0]], 
                    y=serie_filtrata, 
                    name=scelta,
                    mode='lines+markers',
                    connectgaps=False
                ))
                
                diag["Sensore"] = scelta
                stats_final.append(diag)

            # Layout Grafico Dinamico
            fig.update_layout(
                template="plotly_white",
                height=600,
                hovermode="x unified",
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1d", step="day", stepmode="backward"),
                            dict(count=7, label="1w", step="day", stepmode="backward"),
                            dict(step="all")
                        ])
                    ),
                    rangeslider=dict(visible=True),
                    type="date"
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- DIAGNOSTICA ---
            st.subheader("📊 Report Analisi (Zeri e Gauss)")
            if stats_final:
                df_stats = pd.DataFrame(stats_final).set_index("Sensore")
                st.table(df_stats)

            # --- EXPORT WORD ---
            if st.button("Genera Report Word"):
                st.info("Funzionalità export in preparazione...")
                # Qui si può integrare la funzione genera_report_word definita in precedenza

    except Exception as e:
        st.error(f"Errore nel caricamento: {e}")
else:
    st.info("Carica un file dal menu laterale per iniziare.")
