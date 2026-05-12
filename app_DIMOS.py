# =========================================================
# DIMOS - ANALISI TOPOGRAFICA AVANZATA (MODULO TPS)
# VERSIONE OTTIMIZZATA PER INTEGRAZIONE
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import logging
import warnings

# Disabilita warning per pulizia output
warnings.filterwarnings("ignore")

# Logger configurazione
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DIMOS_TPS")

# =========================================================
# FUNZIONI DI UTILITÀ
# =========================================================

def converti_numerico(serie):
    """Converte una serie in numerico gestendo virgole e spazi."""
    return pd.to_numeric(
        serie.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False),
        errors="coerce"
    )

def applica_filtro_sigma(serie, n_sigma=2.0):
    """Rimuove gli outlier basandosi sulla deviazione standard."""
    try:
        serie = converti_numerico(serie)
        media = serie.mean()
        std = serie.std()
        if pd.isna(std) or std == 0:
            return serie
        filtro = (serie >= media - n_sigma * std) & (serie <= media + n_sigma * std)
        return serie.where(filtro)
    except Exception as e:
        logger.error(f"Errore filtro sigma: {e}")
        return serie

@st.cache_data
def carica_excel(uploaded_file):
    """Carica file Excel multi-foglio con gestione errori."""
    data = {}
    try:
        xl = pd.ExcelFile(uploaded_file, engine="openpyxl")
        for sheet in xl.sheet_names:
            try:
                df = xl.parse(sheet, header=0)
                df = df.dropna(how="all")
                df.columns = [str(c).strip() for c in df.columns]
                data[sheet] = df
            except Exception as e:
                logger.warning(f"Errore foglio {sheet}: {e}")
        return data
    except Exception as e:
        logger.error(f"Errore caricamento Excel: {e}")
        return {}

# =========================================================
# FUNZIONE PRINCIPALE (CHIAMATA DA APP_DIMOS)
# =========================================================

def run_tps_monitoring():
    st.title("📐 Monitoraggio TPS")
    st.markdown("Analisi avanzata dei dati topografici con filtraggio statistico.")

    # SIDEBAR LOCALE - CARICAMENTO
    st.sidebar.markdown("---")
    st.sidebar.subheader("📂 Caricamento Dati TPS")
    uploaded_file = st.sidebar.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"], key="tps_uploader")

    if uploaded_file is None:
        st.info("In attesa del caricamento di un file Excel per l'analisi TPS.")
        return

    # ELABORAZIONE
    dfs = carica_excel(uploaded_file)
    if not dfs:
        st.error("Il file caricato non contiene dati validi.")
        return

    fogli = list(dfs.keys())
    st.sidebar.success(f"Trovati {len(fogli)} punti/fogli")

    # SELEZIONE PUNTI
    seleziona_tutti = st.sidebar.checkbox("Seleziona tutti i punti")
    if seleziona_tutti:
        punti = fogli
    else:
        punti = st.sidebar.multiselect("Seleziona punti specifici", fogli)

    if not punti:
        st.warning("Seleziona almeno un punto dalla barra laterale per visualizzare i grafici.")
        return

    # METODO ANALISI
    metodo = st.sidebar.radio("Metodo elaborazione", ["Dati Completi", "Filtro Sigma (Gauss)"])
    n_sigma = 2.0
    if metodo == "Filtro Sigma (Gauss)":
        n_sigma = st.sidebar.slider("Soglia Sigma (Gauss)", 1.0, 5.0, 2.0, 0.5)

    # LOOP VISUALIZZAZIONE PUNTI
    for punto in punti:
        st.markdown(f"### 📍 Punto: **{punto}**")
        
        try:
            df = dfs[punto].copy()
            
            # Gestione Date
            col_data = df.columns[0]
            df[col_data] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)
            df = df.dropna(subset=[col_data]).sort_values(col_data)

            if df.empty:
                st.warning(f"Nessun dato temporale valido per il punto {punto}.")
                continue

            # Identificazione Colonne Numeriche
            colonne_numeriche = []
            for c in df.columns[1:]:
                if "Unnamed" in str(c): continue
                test = converti_numerico(df[c])
                if test.notnull().sum() > 0:
                    colonne_numeriche.append(c)

            if not colonne_numeriche:
                st.warning("Nessun dato numerico trovato in questo foglio.")
                continue

            # Selezione Sensori/Assi
            selezionate = st.multiselect(f"Assi da visualizzare ({punto})", colonne_numeriche, default=[colonne_numeriche[0]], key=f"sel_{punto}")

            # Calcolo Metriche e Grafico
            if selezionate:
                # Metriche in colonne
                m_cols = st.columns(len(selezionate))
                for i, col_name in enumerate(selezionate):
                    serie_m = converti_numerico(df[col_name]).dropna()
                    if not serie_m.empty:
                        m_cols[i].metric(label=col_name, value=f"{serie_m.iloc[-1]:.3f}", delta=f"R: {(serie_m.max()-serie_m.min()):.3f}")

                # Plotly Chart
                fig = go.Figure()
                for col_name in selezionate:
                    d_plot = df[[col_data, col_name]].copy()
                    d_plot[col_name] = converti_numerico(d_plot[col_name])
                    
                    if metodo == "Filtro Sigma (Gauss)":
                        d_plot[col_name] = applica_filtro_sigma(d_plot[col_name], n_sigma)
                    
                    d_plot = d_plot.dropna()
                    
                    if not d_plot.empty:
                        # Dati Reali
                        fig.add_trace(go.Scatter(x=d_plot[col_data], y=d_plot[col_name], mode="lines+markers", name=col_name))
                        
                        # Trendline (Polinomiale Grado 3)
                        if len(d_plot) >= 5:
                            # Trasformazione data in giorni dall'inizio per stabilità numerica
                            x_days = (d_plot[col_data] - d_plot[col_data].min()).dt.total_seconds() / 86400
                            coeff = np.polyfit(x_days, d_plot[col_name], 3)
                            poly = np.poly1d(coeff)
                            fig.add_trace(go.Scatter(x=d_plot[col_data], y=poly(x_days), mode="lines", name=f"Trend {col_name}", line=dict(dash="dot", width=2)))

                fig.update_layout(template="plotly_white", height=500, hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Errore nel processare il punto {punto}.")
            logger.exception(e)

# Supporto esecuzione diretta per test
if __name__ == "__main__":
    # Nota: se eseguito da solo, potrebbe dare errore per mancanza di config pagina, 
    # ma funzionerà perfettamente se chiamato da APP_DIMOS.py
    run_tps_monitoring()
