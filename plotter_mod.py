import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from io import BytesIO
from docx import Document
from docx.shared import Inches

def pulisci_dato_vettoriale(serie, n_sigma, drop_zeros):
    res = serie.copy()
    counts = {"zeri": 0, "gauss": 0}
    if drop_zeros:
        counts["zeri"] = int((res == 0).sum())
        res = res.replace(0, np.nan)
    if n_sigma > 0:
        m, s = res.mean(), res.std()
        outliers = (res < m - n_sigma * s) | (res > m + n_sigma * s)
        counts["gauss"] = int(outliers.sum())
        res[outliers] = np.nan
    return res, counts

def run_plotter():
    # Logo e Intestazione
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=350)
    
    st.title("📊 Analisi Grafica e Reportistica")
    
    # CARICAMENTO FILE IN PAGINA PRINCIPALE (Come richiesto)
    up = st.file_uploader("📂 Carica file (CSV, XLSX, XLSM)", type=['csv','xlsx','xlsm'], key="up_plotter")
    
    if up:
        # Caricamento e gestione foglio NAME
        df_name = None
        if up.name.endswith(('.xlsx', '.xlsm')):
            xls = pd.ExcelFile(up)
            if "NAME" in xls.sheet_names:
                df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
            sheet_dati = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]][0]
            df = pd.read_excel(xls, sheet_name=sheet_dati)
        else:
            df = pd.read_csv(up, sep=None, engine='python')
        
        col_t = df.columns[0]
        df[col_t] = pd.to_datetime(df[col_t], dayfirst=True)
        
        # Sidebar con tutti i parametri "persi"
        with st.sidebar:
            st.header("🛠️ Parametri di Filtro")
            sigma = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
            no_zeros = st.checkbox("Rimuovi Zeri", value=True)
            st.divider()
            st.header("📈 Visualizzazione")
            show_trend = st.checkbox("Linea di Tendenza (Polinomiale)", value=True)
            y_min = st.number_input("Limite Minimo Asse Y", value=float(df.iloc[:,1:].min().min()))
            y_max = st.number_input("Limite Massimo Asse Y", value=float(df.iloc[:,1:].max().max()))

        # Mappatura nomi sensori
        nodi = {}
        for i, col in enumerate(df.columns[1:], 1):
            label = str(df_name.iloc[1, i]) if df_name is not None else col
            nodi[col] = label

        sel = st.multiselect("Seleziona Sensori:", options=list(nodi.keys()), format_func=lambda x: nodi[x])

        if sel:
            fig = go.Figure()
            for c in sel:
                y_p, _ = pulisci_dato_vettoriale(df[c], sigma, no_zeros)
                fig.add_trace(go.Scatter(x=df[col_t], y=y_p, name=nodi[c], mode='lines'))
            
            fig.update_layout(template="plotly_white", yaxis=dict(range=[y_min, y_max]))
            st.plotly_chart(fig, use_container_width=True)

            # --- REPORT WORD (RIPRISTINATO E FUNZIONANTE) ---
            if st.button("🚀 GENERA REPORT WORD"):
                doc = Document()
                doc.add_heading('Report Monitoraggio DIMOS', 0)
                
                for c in sel:
                    y_p, diag = pulisci_dato_vettoriale(df[c], sigma, no_zeros)
                    
                    # Creazione grafico Matplotlib per Word
                    plt.figure(figsize=(10, 5))
                    plt.plot(df[col_t], y_p, label=nodi[c], color='blue')
                    if show_trend:
                        # Calcolo trend su dati puliti
                        valid = ~np.isnan(y_p)
                        z = np.polyfit(mdates.date2num(df[col_t][valid]), y_p[valid], 3)
                        p = np.poly1d(z)
                        plt.plot(df[col_t], p(mdates.date2num(df[col_t])), "r--", label="Trend")
                    
                    plt.title(f"Sensore: {nodi[c]}")
                    plt.legend()
                    plt.grid(True)
                    
                    buf = BytesIO()
                    plt.savefig(buf, format='png')
                    plt.close()
                    
                    doc.add_heading(f"Analisi {nodi[c]}", level=2)
                    doc.add_paragraph(f"Filtri applicati: Gauss {sigma}σ, Zeri rimossi: {diag['zeri']}")
                    doc.add_picture(buf, width=Inches(6))
                
                out = BytesIO()
                doc.save(out)
                st.download_button("⬇️ SCARICA DOCX", out.getvalue(), "Report.docx")
