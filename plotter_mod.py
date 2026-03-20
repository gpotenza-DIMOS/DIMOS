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

try:
    from docx import Document
    from docx.shared import Inches
    WORD_OK = True
except ImportError:
    WORD_OK = False

@st.cache_data(show_spinner=False)
def carica_file_plotter(uploaded_file):
    if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
        xls = pd.ExcelFile(uploaded_file)
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None) if "NAME" in xls.sheet_names else None
        sheet_dati = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]][0]
        df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
    else:
        df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')
        df_name = None
    
    col_t = df_dati.columns[0]
    df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
    df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)
    return df_dati, df_name

def pulisci_vettoriale(serie, n_sigma, drop_zeros):
    res = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    if drop_zeros:
        diag["zeri"] = int((res == 0).sum())
        res = res.replace(0, np.nan)
    
    if n_sigma > 0:
        m, s = res.mean(), res.std()
        outliers = (res < m - n_sigma * s) | (res > m + n_sigma * s)
        diag["gauss"] = int(outliers.sum())
        res[outliers] = np.nan
    return res, diag

def run_plotter():
    if os.path.exists("logo_dimos.jpg"): st.image("logo_dimos.jpg", width=400)
    st.markdown("# 📊 Visualizzazione e Reportistica")
    
    # Caricamento file in pagina principale
    up = st.file_uploader("📂 Carica file dati (Excel/CSV)", type=['xlsx', 'xlsm', 'csv', 'txt'])
    
    with st.sidebar:
        st.header("⚙️ Parametri Analisi")
        sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
        rimuovi_zeri = st.checkbox("Ignora Valori Zero", value=True)
        show_trend = st.checkbox("Mostra Trend (Polinomiale 3°)", value=True)
        max_pts = st.number_input("Punti max grafico (Downsampling)", value=2000)

    if up:
        df_dati, df_name = carica_file_plotter(up)
        st.session_state['df_values'] = df_dati # Per modulo mappa
        st.session_state['col_tempo'] = df_dati.columns[0]
        
        # Mapping Gerarchico (Ottimizzato)
        gerarchia = {}
        for i, col in enumerate(df_dati.columns[1:], 1):
            # Logica di parsing nomi basata su file DIMOS standard
            label = str(df_name.iloc[1, i]) if df_name is not None else col
            gerarchia[col] = label

        sel_cols = st.multiselect("Seleziona Sensori da visualizzare:", options=list(gerarchia.keys()), format_func=lambda x: gerarchia[x])

        if sel_cols:
            fig = go.Figure()
            for c in sel_cols:
                y_p, _ = pulisci_vettoriale(df_dati[c], sigma_val, rimuovi_zeri)
                # Downsampling per fluidità
                step = max(1, len(y_p) // max_pts)
                fig.add_trace(go.Scatter(x=df_dati[df_dati.columns[0]][::step], y=y_p[::step], name=gerarchia[c]))
            
            fig.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)

            # --- SEZIONE STAMPA WORD ---
            st.divider()
            if st.button("🚀 GENERA REPORT WORD COMPLETO") and WORD_OK:
                doc = Document()
                doc.add_heading('Report Monitoraggio DIMOS', 0)
                progress = st.progress(0)
                
                for idx, c in enumerate(sel_cols):
                    y_c, diag = pulisci_vettoriale(df_dati[c], sigma_val, rimuovi_zeri)
                    temp_df = pd.DataFrame({'T': df_dati[df_dati.columns[0]], 'V': y_c}).dropna()
                    
                    if not temp_df.empty:
                        plt.figure(figsize=(8, 4))
                        plt.plot(temp_df['T'], temp_df['V'], label=gerarchia[c], color='#1f77b4', lw=1)
                        if show_trend and len(temp_df) > 10:
                            x_n = mdates.date2num(temp_df['T'])
                            z = np.polyfit(x_n, temp_df['V'], 3)
                            p = np.poly1d(z)
                            plt.plot(temp_df['T'], p(x_n), "r--", alpha=0.8, label="Trend")
                        
                        plt.title(f"Sensore: {gerarchia[c]}")
                        plt.grid(True, alpha=0.3)
                        plt.legend()
                        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
                        
                        buf = BytesIO()
                        plt.savefig(buf, format='png', dpi=100)
                        plt.close()
                        buf.seek(0)
                        
                        doc.add_heading(f'Analisi: {gerarchia[c]}', level=2)
                        doc.add_paragraph(f"Filtri: {diag['zeri']} zeri rimossi, {diag['gauss']} outliers (Gauss).")
                        doc.add_picture(buf, width=Inches(6))
                    progress.progress((idx + 1) / len(sel_cols))
                
                out_buf = BytesIO()
                doc.save(out_buf)
                st.download_button("⬇️ Scarica Report .docx", out_buf.getvalue(), "Report_DIMOS.docx")
