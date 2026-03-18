import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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

def main():
    st.title("📈 Plotter Avanzato (Filtro per Datalogger)")

    uploaded_file = st.file_uploader("Carica file Excel o CSV", type=["csv", "xlsx", "xls"])

    if uploaded_file:
        try:
            # Caricamento (gestione separatore per CSV)
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df = pd.read_excel(uploaded_file)

            # --- IDENTIFICAZIONE DATALOGGER ---
            # Cerchiamo i prefissi (es. "CO_9286") prima del primo spazio o underscore
            tutte_le_colonne = [c for c in df.columns if c.lower() not in ["data e ora", "data", "time", "timestamp"]]
            
            # Estraiamo i nomi univoci dei datalogger dai nomi delle colonne
            lista_datalogger = sorted(list(set([c.split(' ')[0] for c in tutte_le_colonne])))

            # --- SIDEBAR CONTROLLI ---
            st.sidebar.header("🎯 Selezione Dati")
            
            sel_datalogger = st.sidebar.selectbox("1. Seleziona Datalogger", ["TUTTI"] + lista_datalogger)
            
            # Filtriamo le colonne in base al datalogger scelto
            if sel_datalogger == "TUTTI":
                colonne_disponibili = tutte_le_colonne
            else:
                colonne_disponibili = [c for c in tutte_le_colonne if c.startswith(sel_datalogger)]

            sel_sensori = st.sidebar.multiselect(f"2. Sensori di {sel_datalogger}", colonne_disponibili)

            st.sidebar.divider()
            st.sidebar.subheader("🛡️ Parametri Filtro")
            rimuovi_zeri = st.sidebar.checkbox("Rimuovi Zeri", value=True)
            sigma = st.sidebar.slider("Sigma Gauss (Outliers)", 0.0, 5.0, 3.0, 0.5)
            
            st.sidebar.divider()
            st.sidebar.subheader("📅 Asse X")
            modo_x = st.sidebar.radio("Visualizzazione", ["Data Reale", "Equidistante"])
            if modo_x == "Equidistante":
                passo = st.sidebar.number_input("Passo Etichette", 1, 100, 10)

            # --- RICONOSCIMENTO COLONNA TEMPO ---
            col_tempo = next((c for c in df.columns if "data" in c.lower() or "time" in c.lower()), df.columns[0])
            df[col_tempo] = pd.to_datetime(df[col_tempo], errors='ignore')

            # --- GENERAZIONE GRAFICO ---
            if sel_sensori:
                fig = go.Figure()
                stats = {}

                for col in sel_sensori:
                    serie_pulita, diag = applica_filtri_completi(df[col], sigma, rimuovi_zeri)
                    stats[col] = diag
                    
                    x_data = df[col_tempo] if modo_x == "Data Reale" else df[col_tempo].astype(str)
                    
                    fig.add_trace(go.Scatter(
                        x=x_data, 
                        y=serie_pulita, 
                        name=col, 
                        mode='lines+markers',
                        connectgaps=False # Importante per vedere dove mancano dati
                    ))

                fig.update_layout(
                    template="plotly_white",
                    hovermode="x unified",
                    xaxis_title=col_tempo,
                    yaxis_title="Valore",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )

                if modo_x == "Equidistante":
                    fig.update_xaxes(tickvals=df[col_tempo].astype(str)[::passo])

                st.plotly_chart(fig, use_container_width=True)
                
                # Tabella diagnostica
                with st.expander("🔍 Dettaglio punti rimossi"):
                    st.table(pd.DataFrame(stats).T)
            else:
                st.info("Scegli un datalogger e seleziona i sensori nella sidebar.")

        except Exception as e:
            st.error(f"Errore: {e}")

if __name__ == "__main__":
    main()
