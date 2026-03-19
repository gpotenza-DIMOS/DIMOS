import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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

# --- CACHE DATI ---
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
    return "DL", col_name, "Dato"

def run_plotter():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    st.markdown("# Visualizzazione e Stampa Report")

    with st.sidebar:
        st.header("⚙️ Parametri")
        sigma_val = st.slider("Gauss", 0.0, 5.0, 3.0)
        rimuovi_zeri = st.checkbox("Rimuovi 0", value=True)
        show_trend = st.checkbox("Trend 3° grado", value=True)

    uploaded_file = st.file_uploader("📂 Carica Excel", type=['xlsx', 'xlsm'])

    if uploaded_file:
        df_dati, df_name = carica_file_cache(uploaded_file)
        col_t = df_dati.columns[0]
        
        gerarchia = {}
        for i, col in enumerate(df_dati.columns):
            if i == 0: continue
            dl, sens, param = parse_column_info(col, df_name, i)
            if dl not in gerarchia: gerarchia[dl] = {}
            if sens not in gerarchia[dl]: gerarchia[dl][sens] = {}
            gerarchia[dl][sens][param] = col

        # Visualizzazione (Plotly)
        st.subheader("📊 Anteprima Grafico")
        cv1, cv2, cv3 = st.columns(3)
        with cv1: sel_dl = st.multiselect("Datalogger", sorted(gerarchia.keys()))
        with cv2:
            s_opts = sorted(list(set([s for d in sel_dl for s in gerarchia[d].keys()])))
            sel_sens = st.multiselect("Sensori", s_opts)
        with cv3:
            p_opts = sorted(list(set([p for d in sel_dl for s in sel_sens if s in gerarchia[d] for p in gerarchia[d][s].keys()])))
            sel_params = st.multiselect("Grandezze", p_opts)

        if sel_params:
            fig = go.Figure()
            for d in sel_dl:
                for s in sel_sens:
                    if s in gerarchia[d]:
                        for p in sel_params:
                            if p in gerarchia[d][s]:
                                y_v, _ = pulisci_dati(df_dati[gerarchia[d][s][p]], sigma_val, rimuovi_zeri)
                                fig.add_trace(go.Scatter(x=df_dati[col_t], y=y_v, name=f"{s}-{p}"))
            st.plotly_chart(fig, use_container_width=True)

        # STAMPA CORRETTA (FORZATA)
        st.divider()
        if st.button("🚀 GENERA REPORT WORD") and WORD_OK:
            doc = Document()
            doc.add_heading('Report Monitoraggio DIMOS', 0)
            
            with st.spinner("Creazione grafici in corso..."):
                for d in sel_dl:
                    doc.add_heading(f'Centralina: {d}', level=1)
                    for s in sel_sens:
                        if s in gerarchia[d]:
                            p_finali = [p for p in sel_params if p in gerarchia[d][s]]
                            for p in p_finali:
                                col_id = gerarchia[d][s][p]
                                y_c, diag = pulisci_dati(df_dati[col_id], sigma_val, rimuovi_zeri)
                                
                                # Prepariamo i dati eliminando i NaN per Matplotlib
                                df_temp = pd.DataFrame({'Data': df_dati[col_t], 'Valore': y_c}).dropna()
                                
                                plt.figure(figsize=(9, 4.5))
                                if not df_temp.empty:
                                    # PLOT ESPLICITO
                                    plt.plot(df_temp['Data'], df_temp['Valore'], color='#004d99', linewidth=1.2, label=p, marker='.', markersize=2)
                                    
                                    if show_trend and len(df_temp) > 5:
                                        # Calcolo trend su timestamp numerico
                                        x_num = df_temp['Data'].apply(lambda x: x.timestamp())
                                        poly = np.poly1d(np.polyfit(x_num, df_temp['Valore'], 3))
                                        plt.plot(df_temp['Data'], poly(x_num), color='red', linestyle='--', linewidth=1.5, label='Trend')
                                
                                plt.title(f"{s} - {p}", fontsize=12, pad=15)
                                plt.grid(True, linestyle='--', alpha=0.5)
                                plt.legend(loc='upper right')
                                
                                # Formattazione date asse X
                                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
                                plt.gcf().autofmt_xdate()
                                
                                img_buf = BytesIO()
                                plt.savefig(img_buf, format='png', dpi=110, bbox_inches='tight')
                                plt.close()
                                img_buf.seek(0)
                                
                                doc.add_heading(f'Sensore: {s} | {p}', level=2)
                                doc.add_paragraph(f"Statistiche: Zeri rimossi {diag['zeri']} | Outliers {diag['gauss']}")
                                doc.add_picture(img_buf, width=Inches(5.8))
                                img_buf.close()

            f_buf = BytesIO()
            doc.save(f_buf)
            f_buf.seek(0)
            st.download_button("⬇️ SCARICA REPORT", f_buf.getvalue(), "Report_DIMOS_Finale.docx")

if __name__ == "__main__":
    run_plotter()
