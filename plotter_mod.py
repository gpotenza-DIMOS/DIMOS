import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re
from datetime import datetime

# --- MOTORE DI PULIZIA DATI (Invariato) ---
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

def parse_column_info(col_name, df_name=None, col_index=None):
    """
    Riconosce DL, Sensore e Parametro sia da foglio NAME che da stringa Web.
    """
    # 1. TENTATIVO CON FOGLIO NAME
    if df_name is not None and col_index is not None:
        try:
            dl = str(df_name.iloc[0, col_index]).strip()
            sens = str(df_name.iloc[1, col_index]).strip()
            web_info = str(df_name.iloc[2, col_index]).strip() if len(df_name) > 2 else col_name
            
            # Estrazione unità e parametro dal nome web (riga 3)
            unit_match = re.search(r'\[(.*?)\]', web_info)
            unit = f" [{unit_match.group(1)}]" if unit_match else ""
            
            # Cerca se nel web_info c'è un suffisso tipo _X, _Y, _LI
            param_match = re.search(r'_(X|Y|Z|T1|T2|LI|LQ|LM|VAR\d+)', web_info)
            param = param_match.group(1) if param_match else web_info.split()[-1].replace(unit.strip(), "").strip()
            
            return dl, sens, f"{param}{unit}"
        except:
            pass

    # 2. FALLBACK: PARSING STRINGA WEB (es. CO_9277 CL_01_X [°])
    unit_match = re.search(r'\[(.*?)\]', col_name)
    unit = f" [{unit_match.group(1)}]" if unit_match else ""
    clean_name = re.sub(r'\[.*?\]', '', col_name).strip()
    parts = clean_name.split()
    
    dl = parts[0] if len(parts) > 0 else "DL_Generico"
    
    if len(parts) > 1:
        full_sens = parts[1]
        # Separa Sensore da Parametro (es CL_01_X -> CL_01 e X)
        sub_parts = full_sens.rsplit('_', 1)
        if len(sub_parts) > 1 and len(sub_parts[1]) in [1, 2, 3]: # X, Y, T1, LI...
            sens_base = sub_parts[0]
            param = sub_parts[1]
        else:
            sens_base = full_sens
            param = "Dato"
    else:
        sens_base = "Vari"
        param = "Dato"
        
    return dl, sens_base, f"{param}{unit}"

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
        # Struttura: { DL: { Sensore: { Label_Parametro: Colonna_Originale } } }
        gerarchia = {}
        df_dati = pd.DataFrame()

        try:
            df_name = None
            if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
                xls = pd.ExcelFile(uploaded_file)
                if "NAME" in xls.sheet_names:
                    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
                sheet_dati = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]][0]
                df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
            else:
                df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')

            # Pulizia date
            col_t = df_dati.columns[0]
            df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
            df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)

            # Costruzione gerarchia intelligente
            for i, col in enumerate(df_dati.columns):
                if i == 0: continue
                dl, sens, param = parse_column_info(col, df_name, i)
                
                if dl not in gerarchia: gerarchia[dl] = {}
                if sens not in gerarchia[dl]: gerarchia[dl][sens] = {}
                gerarchia[dl][sens][param] = col

            # --- SELEZIONE UI A 3 LIVELLI ---
            st.subheader("🔍 Selezione Configurazione")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                sel_dl = st.multiselect("1. Datalogger", options=sorted(gerarchia.keys()))
            
            with c2:
                opts_sens = []
                for d in sel_dl: opts_sens.extend(gerarchia[d].keys())
                sel_sens = st.multiselect("2. Sensori", options=sorted(list(set(opts_sens))))
            
            with c3:
                opts_param = []
                for d in sel_dl:
                    for s in sel_sens:
                        if s in gerarchia[d]:
                            opts_param.extend(gerarchia[d][s].keys())
                sel_params = st.multiselect("3. Grandezze (X, Y, LI, T...)", options=sorted(list(set(opts_param))))

            # Filtro Tempo
            st.write("---")
            min_d, max_d = df_dati[col_t].min().date(), df_dati[col_t].max().date()
            t1, t2 = st.columns(2)
            with t1: start_dt = st.date_input("Inizio", min_d)
            with t2: end_dt = st.date_input("Fine", max_d)

            # --- PLOT ---
            targets = []
            for d in sel_dl:
                for s in sel_sens:
                    if s in gerarchia[d]:
                        for p in sel_params:
                            if p in gerarchia[d][s]:
                                targets.append((gerarchia[d][s][p], f"{s} - {p}"))

            if targets:
                mask = (df_dati[col_t].dt.date >= start_dt) & (df_dati[col_t].dt.date <= end_dt)
                df_p = df_dati.loc[mask].copy()
                if not df_p.empty:
                    fig = go.Figure()
                    colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]
                    for idx, (col_id, display_name) in enumerate(targets):
                        color = colors[idx % len(colors)]
                        y_vals, _ = pulisci_dati(df_p[col_id], sigma_val, rimuovi_zeri)
                        
                        fig.add_trace(go.Scatter(
                            x=df_p[col_t], y=y_vals, name=display_name,
                            mode='lines+markers', line=dict(color=color, width=1.5), marker=dict(size=4)
                        ))

                        if show_trend:
                            v_idx = y_vals.notna()
                            if v_idx.sum() > 4:
                                x_ts = df_p.loc[v_idx, col_t].apply(lambda x: x.timestamp())
                                poly = np.poly1d(np.polyfit(x_ts, y_vals[v_idx], 3))
                                fig.add_trace(go.Scatter(
                                    x=df_p[col_t], y=poly(df_p[col_t].apply(lambda x: x.timestamp())),
                                    name=f"Trend {display_name}", line=dict(color=color, width=2, dash='dash'), opacity=0.5
                                ))

                    fig.update_layout(height=700, template="plotly_white", xaxis=dict(rangeslider=dict(visible=True)))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Nessun dato nel periodo selezionato.")
        except Exception as e:
            st.error(f"Errore: {e}")

if __name__ == "__main__":
    run_plotter()
