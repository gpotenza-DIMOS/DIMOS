import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re
from datetime import datetime
from io import BytesIO

# --- GESTIONE LIBRERIE (Invariate) ---
try:
    from docx import Document
    from docx.shared import Inches
    WORD_OK = True
except ImportError:
    WORD_OK = False

# --- CACHE E OTTIMIZZAZIONE (Velocità Massima) ---
@st.cache_data(show_spinner=False)
def carica_dati_ottimizzato(uploaded_file):
    df_name = None
    if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
        xls = pd.ExcelFile(uploaded_file)
        if "NAME" in xls.sheet_names:
            df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        sheet_dati = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]][0]
        df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
    else:
        df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')
    
    col_t = df_dati.columns[0]
    df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
    df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)
    return df_dati, df_name

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
    if df_name is not None and col_index is not None:
        try:
            dl = str(df_name.iloc[0, col_index]).strip()
            sens = str(df_name.iloc[1, col_index]).strip()
            web_info = str(df_name.iloc[2, col_index]).strip() if len(df_name) > 2 else col_name
            unit_match = re.search(r'\[(.*?)\]', web_info)
            unit = f" [{unit_match.group(1)}]" if unit_match else ""
            param_match = re.search(r'_(X|Y|Z|T1|T2|LI|LQ|LM|VAR\d+)', web_info)
            param = param_match.group(1) if param_match else web_info.split()[-1].replace(unit.strip(), "").strip()
            return dl, sens, f"{param}{unit}"
        except: pass
    unit_match = re.search(r'\[(.*?)\]', col_name)
    unit = f" [{unit_match.group(1)}]" if unit_match else ""
    clean_name = re.sub(r'\[.*?\]', '', col_name).strip()
    parts = clean_name.split()
    dl = parts[0] if len(parts) > 0 else "DL_Generico"
    if len(parts) > 1:
        full_sens = parts[1]
        sub_parts = full_sens.rsplit('_', 1)
        if len(sub_parts) > 1 and len(sub_parts[1]) in [1, 2, 3]:
            sens_base, param = sub_parts[0], sub_parts[1]
        else: sens_base, param = full_sens, "Dato"
    else: sens_base, param = "Vari", "Dato"
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

    uploaded_file = st.file_uploader("📂 Carica file Excel o CSV", type=['xlsx', 'xlsm', 'csv'])

    if uploaded_file:
        df_dati, df_name = carica_dati_ottimizzato(uploaded_file)
        col_t = df_dati.columns[0]

        gerarchia = {}
        for i, col in enumerate(df_dati.columns):
            if i == 0: continue
            dl, sens, param = parse_column_info(col, df_name, i)
            if dl not in gerarchia: gerarchia[dl] = {}
            if sens not in gerarchia[dl]: gerarchia[dl][sens] = {}
            gerarchia[dl][sens][param] = col

        # --- SELEZIONE UI ---
        st.subheader("🔍 Selezione Configurazione")
        c1, c2, c3 = st.columns(3)
        with c1: sel_dl = st.multiselect("1. Datalogger", options=sorted(gerarchia.keys()))
        with c2:
            opts_sens = []
            for d in sel_dl: opts_sens.extend(gerarchia[d].keys())
            sel_sens = st.multiselect("2. Sensori", options=sorted(list(set(opts_sens))))
        with c3:
            opts_param = []
            for d in sel_dl:
                for s in sel_sens:
                    if s in gerarchia[d]: opts_param.extend(gerarchia[d][s].keys())
            sel_params = st.multiselect("3. Grandezze", options=sorted(list(set(opts_param))))

        # --- GESTIONE GRAFICO (Visualizzazione Fluida) ---
        targets = []
        for d in sel_dl:
            for s in sel_sens:
                if s in gerarchia[d]:
                    for p in sel_params:
                        if p in gerarchia[d][s]: targets.append((gerarchia[d][s][p], f"{s} - {p}"))

        if targets:
            fig = go.Figure()
            colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]
            report_stats = []

            for idx, (col_id, display_name) in enumerate(targets):
                color = colors[idx % len(colors)]
                y_vals, diag = pulisci_dati(df_dati[col_id], sigma_val, rimuovi_zeri)
                diag["Parametro"] = display_name
                report_stats.append(diag)

                # Dati Reali
                fig.add_trace(go.Scatter(
                    x=df_dati[col_t], y=y_vals, name=display_name,
                    mode='lines+markers', line=dict(color=color, width=1.2),
                    marker=dict(size=3)
                ))

                # Trend
                if show_trend:
                    v_idx = y_vals.notna()
                    if v_idx.sum() > 4:
                        x_ts = df_dati.loc[v_idx, col_t].apply(lambda x: x.timestamp())
                        poly = np.poly1d(np.polyfit(x_ts, y_vals[v_idx], 3))
                        fig.add_trace(go.Scatter(
                            x=df_dati[col_t], y=poly(df_dati[col_t].apply(lambda x: x.timestamp())),
                            name=f"Trend {display_name}", line=dict(color=color, width=2, dash='dash'), opacity=0.4
                        ))

            fig.update_layout(
                height=650, template="plotly_white",
                xaxis=dict(title="Data", rangeslider=dict(visible=True), type='date'),
                legend=dict(orientation="h", y=-0.2)
            )
            # NOTA: Usiamo il RangeSlider nativo di Plotly per lo zoom istantaneo
            st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})
            st.table(pd.DataFrame(report_stats).set_index("Parametro"))

        # --- SEZIONE STAMPA WORD (Selettiva come Elettrolivelle) ---
        st.divider()
        st.subheader("📄 Generazione Report Word")
        with st.expander("Configura ed Esporta Report"):
            c_w1, c_w2 = st.columns(2)
            with c_w1:
                sel_dl_w = st.multiselect("Centraline da stampare", options=sorted(gerarchia.keys()), key="dl_word")
            with c_w2:
                opts_p_w = []
                for d in sel_dl_w:
                    for s in gerarchia[d]: opts_p_w.extend(gerarchia[d][s].keys())
                sel_params_w = st.multiselect("Grandezze da includere", options=sorted(list(set(opts_p_w))), key="p_word")

            if st.button("Genera Report .docx") and WORD_OK:
                doc = Document()
                doc.add_heading('Report Monitoraggio DIMOS', 0)
                
                for d in sel_dl_w:
                    doc.add_heading(f'Datalogger: {d}', level=1)
                    for s in gerarchia[d]:
                        # Filtra solo i parametri scelti dall'utente per la stampa
                        params_to_print = [p for p in gerarchia[d][s] if p in sel_params_w]
                        if params_to_print:
                            doc.add_heading(f'Sensore: {s}', level=2)
                            for p in params_to_print:
                                col_id = gerarchia[d][s][p]
                                y_clean, diag = pulisci_dati(df_dati[col_id], sigma_val, rimuovi_zeri)
                                doc.add_paragraph(f"Parametro: {p} | Zeri rimossi: {diag['zeri']} | Outliers Gauss: {diag['gauss']}")
                
                buf = BytesIO()
                doc.save(buf)
                st.download_button("⬇️ Scarica File Word", buf.getvalue(), "Report_Monitoraggio.docx")

if __name__ == "__main__":
    run_plotter()
