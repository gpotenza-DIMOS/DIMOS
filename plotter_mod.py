import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import re

# --- LOGICA FILTRI (GAUSS & ZERI) ---
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

# --- PARSER GERARCHICO ---
def get_hierarchy(df_data, df_name=None):
    """
    Crea un dizionario: { Datalogger: { Sensore: [Lista Colonne/Misure] } }
    """
    hierarchy = {}
    cols = [c for c in df_data.columns if not any(x in c.lower() for x in ["data", "time", "ora"])]

    if df_name is not None:
        # Logica basata sul foglio NAME (Riga 1: Datalogger, Riga 2: Sensore, Riga 3: Nome Web)
        for i, col_web in enumerate(df_data.columns):
            if col_web in cols:
                # Cerchiamo la corrispondenza nel foglio NAME
                try:
                    dl = str(df_name.iloc[0, i]).strip()
                    sens = str(df_name.iloc[1, i]).strip()
                    if dl not in hierarchy: hierarchy[dl] = {}
                    if sens not in hierarchy[dl]: hierarchy[dl][sens] = []
                    hierarchy[dl][sens].append(col_web)
                except:
                    pass
    else:
        # Logica Fallback: Parsing del nome web (es. CO_9277 CL_01_X [°])
        for c in cols:
            parts = c.split(' ')
            dl = parts[0] # CO_9277
            # Il resto è il sensore + misura
            sens_full = " ".join(parts[1:]) if len(parts) > 1 else "Generico"
            
            if dl not in hierarchy: hierarchy[dl] = {}
            if sens_full not in hierarchy[dl]: hierarchy[dl][sens_full] = []
            hierarchy[dl][sens_full].append(c)
            
    return hierarchy

def main():
    st.title("📈 DIMOS Professional Plotter")

    uploaded_file = st.file_uploader("Carica File Monitoraggio", type=["xlsx", "csv"])

    if uploaded_file:
        try:
            # Caricamento Dati e eventuale foglio NAME
            df_name = None
            if uploaded_file.name.endswith('.xlsx'):
                all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
                # Cerchiamo il foglio dati (solitamente il primo o quello con più righe)
                data_sheet_name = list(all_sheets.keys())[0]
                df_data = all_sheets[data_sheet_name]
                if "NAME" in all_sheets:
                    df_name = all_sheets["NAME"]
            else:
                df_data = pd.read_csv(uploaded_file, sep=None, engine='python')

            # Analisi Gerarchia
            hierarchy = get_hierarchy(df_data, df_name)
            
            # --- SIDEBAR: SELEZIONE GERARCHICA ---
            st.sidebar.header("🔎 Selezione Sensori")
            
            sel_dl = st.sidebar.multiselect("1. Seleziona Datalogger", list(hierarchy.keys()))
            
            all_relevant_cols = []
            if sel_dl:
                for dl in sel_dl:
                    st.sidebar.markdown(f"**Datalogger: {dl}**")
                    sensori_disponibili = hierarchy[dl]
                    sel_sens = st.sidebar.multiselect(f"Sensori per {dl}", list(sensori_disponibili.keys()), key=f"sens_{dl}")
                    for s in sel_sens:
                        all_relevant_cols.extend(sensori_disponibili[s])

            # --- FILTRI ---
            st.sidebar.divider()
            st.sidebar.subheader("🛡️ Analisi e Filtri")
            rimuovi_zeri = st.sidebar.checkbox("Rimuovi Zeri (0.00)", value=True)
            sigma = st.sidebar.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0, 0.5)

            # --- GESTIONE ASCISSE ---
            st.sidebar.divider()
            st.sidebar.subheader("📅 Impostazione Asse X")
            col_tempo = next((c for c in df_data.columns if "data" in c.lower() or "ora" in c.lower()), df_data.columns[0])
            df_data[col_tempo] = pd.to_datetime(df_data[col_tempo], errors='coerce')
            
            modo_x = st.sidebar.radio("Tipo Ascisse", ["Temporale Reale", "Testo (Equidistante)"])
            passo_x = st.sidebar.number_input("Passo etichette (ogni N righe)", 1, 500, 20) if modo_x == "Testo (Equidistante)" else 1

            # --- GRAFICO ---
            if all_relevant_cols:
                fig = go.Figure()
                stats = {}

                for col in all_relevant_cols:
                    y_f, d = applica_filtri_completi(df_data[col], sigma, rimuovi_zeri)
                    stats[col] = d
                    
                    if modo_x == "Temporale Reale":
                        x_axis = df_data[col_tempo]
                    else:
                        x_axis = df_data[col_tempo].dt.strftime('%d/%m/%y %H:%M')

                    fig.add_trace(go.Scatter(x=x_axis, y=y_f, name=col, mode='lines+markers'))

                fig.update_layout(
                    template="plotly_white",
                    height=650,
                    xaxis_title="Tempo",
                    yaxis_title="Valore Misurato",
                    legend=dict(orientation="h", y=-0.2)
                )
                
                if modo_x == "Testo (Equidistante)":
                    fig.update_xaxes(tickmode='array', 
                                    tickvals=df_data.index[::passo_x], 
                                    ticktext=df_data[col_tempo].dt.strftime('%d/%m/%y %H:%M')[::passo_x])

                st.plotly_chart(fig, use_container_width=True)

                # Riepilogo Diagnostica
                with st.expander("📊 Report Analisi (Punti rimossi)"):
                    st.table(pd.DataFrame(stats).T)
                
                # Bottone per Stampa/Export (Placeholder per logica Word)
                if st.button("📄 Genera Anteprima per Report"):
                    st.success("Analisi completata. Pronto per l'esportazione.")

            else:
                st.info("Seleziona uno o più datalogger e i relativi sensori dalla sidebar.")

        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")
