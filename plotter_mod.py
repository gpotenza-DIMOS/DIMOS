import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from datetime import datetime
from io import BytesIO

# --- GESTIONE LIBRERIE STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    WORD_OK = True
except ImportError:
    WORD_OK = False

# --- CACHE DATI (Logica Originale) ---
@st.cache_data(show_spinner=False)
def carica_file_cache(uploaded_file):
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

# --- MOTORE PULIZIA ---
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

# --- PARSING GERARCHICO (Stamattina) ---
def parse_column_info(col_name, df_name=None, col_index=None):
    if df_name is not None and col_index is not None:
        try:
            dl = str(df_name.iloc[0, col_index]).strip()
            sens = str(df_name.iloc[1, col_index]).strip()
            web_info = str(df_name.iloc[2, col_index]).strip() if len(df_name) > 2 else col_name
            unit_m = re.search(r'\[(.*?)\]', web_info)
            unit = f" [{unit_m.group(1)}]" if unit_m else ""
            p_match = re.search(r'_(X|Y|Z|T1|T2|LI|LQ|LM|VAR\d+)', web_info)
            param = p_match.group(1) if p_match else web_info.split()[-1].replace(unit.strip(), "").strip()
            return dl, sens, f"{param}{unit}"
        except: pass
    return "Generale", col_name, "Dato"

def run_plotter():
    st.markdown("# 📊 Visualizzazione e Reportistica")
    
    with st.sidebar:
        st.header("⚙️ Parametri")
        sigma_val = st.slider("Filtro Gauss", 0.0, 5.0, 3.0)
        rimuovi_zeri = st.checkbox("Elimina Zeri", value=True)
        show_trend = st.checkbox("Trend 3° grado", value=True)

    uploaded_file = st.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])

    if uploaded_file:
        df_dati, df_name = carica_file_cache(uploaded_file)
        col_t = df_dati.columns[0]
        
        # Salvataggio per modulo Mappe
        st.session_state['df_values'] = df_dati
        st.session_state['col_tempo'] = col_t

        # Costruzione Gerarchia
        gerarchia = {}
        for i, col in enumerate(df_dati.columns):
            if i == 0: continue
            dl, sens, param = parse_column_info(col, df_name, i)
            if dl not in gerarchia: gerarchia[dl] = {}
            if sens not in gerarchia[dl]: gerarchia[dl][sens] = {}
            gerarchia[dl][sens][param] = col

        # SELEZIONE VISUALIZZAZIONE
        c1, c2, c3 = st.columns(3)
        with c1: sel_dl_v = st.multiselect("Datalogger", sorted(gerarchia.keys()))
        with c2:
            s_opts = sorted(list(set([s for d in sel_dl_v for s in gerarchia[d].keys()])))
            sel_sens_v = st.multiselect("Sensori", s_opts)
        with c3:
            p_opts = sorted(list(set([p for d in sel_dl_v for s in sel_sens_v if s in gerarchia[d] for p in gerarchia[d][s].keys()])))
            sel_params_v = st.multiselect("Grandezze", p_opts)

        if sel_params_v:
            fig = go.Figure()
            for d in sel_dl_v:
                for s in sel_sens_v:
                    if s in gerarchia[d]:
                        for p in sel_params_v:
                            if p in gerarchia[d][s]:
                                y_v, _ = pulisci_dati(df_dati[gerarchia[d][s][p]], sigma_val, rimuovi_zeri)
                                fig.add_trace(go.Scatter(x=df_dati[col_t], y=y_v, name=f"{s}-{p}"))
            st.plotly_chart(fig, use_container_width=True)

        # SEZIONE STAMPA (CORRETTA)
        st.divider()
        if st.button("🚀 GENERA REPORT WORD COMPLETO") and WORD_OK:
            doc = Document()
            doc.add_heading('Report Monitoraggio DIMOS', 0)
            
            for d in sel_dl_v:
                doc.add_heading(f'Centralina: {d}', level=1)
                for s in sel_sens_v:
                    if s in gerarchia[d]:
                        p_finali = [p for p in sel_params_v if p in gerarchia[d][s]]
                        for p in p_finali:
                            col_id = gerarchia[d][s][p]
                            y_c, diag = pulisci_dati(df_dati[col_id], sigma_val, rimuovi_zeri)
                            
                            # Grafico Matplotlib
                            plt.figure(figsize=(10, 4))
                            plt.plot(df_dati[col_t], y_c, label=p, color='blue', linewidth=1)
                            if show_trend and y_c.notna().sum() > 5:
                                x_ts = df_dati.loc[y_c.notna(), col_t].apply(lambda x: x.timestamp())
                                poly = np.poly1d(np.polyfit(x_ts, y_c.dropna(), 3))
                                plt.plot(df_dati[col_t], poly(df_dati[col_t].apply(lambda x: x.timestamp())), color='red', linestyle='--')
                            
                            plt.title(f"{s} - {p}")
                            plt.grid(True, alpha=0.3)
                            plt.gcf().autofmt_xdate()
                            
                            # BUFFER IMMAGINE
                            img_stream = BytesIO()
                            plt.savefig(img_stream, format='png', bbox_inches='tight', dpi=100)
                            plt.close()
                            img_stream.seek(0) # <--- QUESTO RISOLVE IL PROBLEMA DEL FILE VUOTO
                            
                            doc.add_heading(f'Sensore: {s} | {p}', level=2)
                            doc.add_paragraph(f"Statistiche: Zeri rimosssi {diag['zeri']} | Outliers Gauss {diag['gauss']}")
                            doc.add_picture(img_stream, width=Inches(6))
            
            out_buf = BytesIO()
            doc.save(out_buf)
            out_buf.seek(0)
            st.download_button("⬇️ Scarica Report", out_buf.getvalue(), "Report_DIMOS_Corretto.docx")

if __name__ == "__main__":
    run_plotter()
