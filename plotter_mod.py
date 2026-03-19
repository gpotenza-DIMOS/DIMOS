import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re
from datetime import datetime
from io import BytesIO

# --- GESTIONE LIBRERIA WORD (Invariata) ---
try:
    from docx import Document
    WORD_OK = True
except ImportError:
    WORD_OK = False

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

def parse_web_name(col_name):
    """Scompone nomi tipo 'CO_9277 CL_01_X [°]' in DL, Sensore, Parametro/Unità"""
    # Regex per estrarre [Unità]
    unit = ""
    match_unit = re.search(r'\[(.*?)\]', col_name)
    if match_unit:
        unit = match_unit.group(1)
    
    clean_name = re.sub(r'\[.*?\]', '', col_name).strip()
    parts = clean_name.split()
    
    dl = parts[0] if len(parts) > 0 else "DL_Sconosciuto"
    
    # Se abbiamo CO_9277 CL_01_X
    if len(parts) > 1:
        full_sens = parts[1]
        # Se c'è un underscore nel nome del sensore (es. CL_01_X), proviamo a separare il parametro finale
        sub_parts = full_sens.rsplit('_', 1)
        if len(sub_parts) > 1 and len(sub_parts[1]) <= 2: # X, Y, Z, T1.. solitamente brevi
            sens_base = sub_parts[0]
            param = sub_parts[1]
        else:
            sens_base = full_sens
            param = ""
    else:
        sens_base = "Generico"
        param = ""
        
    label = f"{param} [{unit}]" if param and unit else (unit if unit else param)
    if not label: label = "Dato"
    
    return dl, sens_base, label

def run_plotter():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
    st.divider()

    with st.sidebar:
        st.header("⚙️ Parametri Modulo")
        sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
        rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
        show_trend = st.checkbox("Mostra Linea di Tendenza (3° grado)", value=True)
        st.divider()

    uploaded_file = st.file_uploader("📂 Carica file Excel (NAME + Dati) o CSV", type=['xlsx', 'xlsm', 'csv'])

    if uploaded_file:
        gerarchia = {} # {DL: {Sensore: {Etichetta: Colonna_Originale}}}
        df_dati = pd.DataFrame()

        try:
            if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]]
                df_dati = pd.read_excel(xls, sheet_name=sheet_names[0])
                
                if "NAME" in xls.sheet_names:
                    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
                    for i, col_name in enumerate(df_dati.columns):
                        if i == 0: continue
                        # Lettura riga 1 (DL), riga 2 (Sensore), riga 3 (Web Name/Unit)
                        dl = str(df_name.iloc[0, i]).strip() if len(df_name) > 0 else "DL"
                        sens_user = str(df_name.iloc[1, i]).strip() if len(df_name) > 1 else "Sensore"
                        web_info = str(df_name.iloc[2, i]).strip() if len(df_name) > 2 else col_name
                        
                        # Parsing del nome web per estrarre l'unità o il parametro (X, Y, Z...)
                        _, _, label = parse_web_name(web_info)
                        final_label = f"{sens_user} - {label}"
                        
                        if dl not in gerarchia: gerarchia[dl] = {}
                        if sens_user not in gerarchia[dl]: gerarchia[dl][sens_user] = {}
                        gerarchia[dl][sens_user][final_label] = col_name
            else:
                df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')

            # Gestione Date
            col_t = df_dati.columns[0]
            df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
            df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)

            # Fallback se non c'è gerarchia (Caricamento CSV o NAME mancante)
            if not gerarchia:
                for col in df_dati.columns[1:]:
                    dl, sens_base, label = parse_web_name(col)
                    if dl not in gerarchia: gerarchia[dl] = {}
                    if sens_base not in gerarchia[dl]: gerarchia[dl][sens_base] = {}
                    gerarchia[dl][sens_base][label] = col

            # --- SELEZIONE UI POTENZIATA ---
            st.subheader("🔍 Selezione Centraline e Sensori")
            c1, c2, c3 = st.columns(3)
            with c1:
                sel_dl = st.multiselect("1. Seleziona Centraline", options=sorted(list(gerarchia.keys())))
            
            with c2:
                all_sens_opts = []
                for d in sel_dl:
                    all_sens_opts.extend(list(gerarchia[d].keys()))
                sel_sens = st.multiselect("2. Seleziona Sensori", options=sorted(list(set(all_sens_opts))))
            
            with c3:
                all_param_opts = []
                for d in sel_dl:
                    for s in sel_sens:
                        if s in gerarchia[d]:
                            all_param_opts.extend(list(gerarchia[d][s].keys()))
                sel_params = st.multiselect("3. Grandezze/Parametri", options=sorted(list(set(all_param_opts))))

            st.write("---")
            min_d, max_d = df_dati[col_t].min().date(), df_dati[col_t].max().date()
            t1, t2 = st.columns(2)
            with t1: start_dt = st.date_input("Inizio Analisi", min_d)
            with t2: end_dt = st.date_input("Fine Analisi", max_d)

            # --- GENERAZIONE GRAFICO ---
            final_cols_to_plot = []
            for d in sel_dl:
                for s in sel_sens:
                    if s in gerarchia[d]:
                        for p in sel_params:
                            if p in gerarchia[d][s]:
                                final_cols_to_plot.append((gerarchia[d][s][p], p))

            if final_cols_to_plot:
                mask = (df_dati[col_t].dt.date >= start_dt) & (df_dati[col_t].dt.date <= end_dt)
                df_p = df_dati.loc[mask].copy()
                
                if not df_p.empty:
                    fig = go.Figure()
                    report_stats = []
                    colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692"]

                    for idx, (col_id, label_display) in enumerate(final_cols_to_plot):
                        color = colors[idx % len(colors)]
                        y_clean, diag = pulisci_dati(df_p[col_id], sigma_val, rimuovi_zeri)
                        diag["Parametro"] = label_display
                        report_stats.append(diag)

                        # Dati Reali
                        fig.add_trace(go.Scatter(
                            x=df_p[col_t], y=y_clean, name=label_display,
                            mode='lines+markers', line=dict(color=color, width=1.5),
                            marker=dict(size=4)
                        ))

                        # Tendenza Polinomiale 3° Grado
                        if show_trend:
                            valid_idx = y_clean.notna()
                            if valid_idx.sum() > 4:
                                x_num = df_p.loc[valid_idx, col_t].apply(lambda x: x.timestamp())
                                coeffs = np.polyfit(x_num, y_clean[valid_idx], 3)
                                poly_func = np.poly1d(coeffs)
                                y_trend = poly_func(df_p[col_t].apply(lambda x: x.timestamp()))
                                fig.add_trace(go.Scatter(
                                    x=df_p[col_t], y=y_trend, name=f"{label_display} (Trend)",
                                    mode='lines', line=dict(color=color, width=2, dash='dash'),
                                    opacity=0.6
                                ))

                    fig.update_layout(
                        height=700, template="plotly_white",
                        xaxis=dict(title="Data", rangeslider=dict(visible=True)),
                        yaxis=dict(title="Valore"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.table(pd.DataFrame(report_stats).set_index("Parametro"))
                else:
                    st.warning("Nessun dato trovato per le date selezionate.")
        except Exception as e:
            st.error(f"Errore: {e}")

if __name__ == "__main__":
    run_plotter()
