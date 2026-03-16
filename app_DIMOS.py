import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Monitoraggio Elettrolivelle", layout="wide")

# --- MOTORE DI CALCOLO (CONGRUENTE VBA) ---
@st.cache_data(show_spinner=False)
def elaborazione_vba_originale(df_values, l_barra, n_sigma):
    # 1. BONIFICA ZERI (Richiesta 1)
    df_values = df_values.replace(0, np.nan)
    
    # Conversione gradi -> mm
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    
    # 2. DELTA SINGOLO (Richiesta 2: Rispetto a prima riga, no cumulata)
    data_c0 = data_mm - data_mm[0, :]
    
    # Filtraggio Outlier Sigma Gauss (Sostituzione con media come VBA Modulo 1)
    data_processed = data_c0.copy()
    means = np.nanmean(data_processed, axis=0)
    stds = np.nanstd(data_processed, axis=0)
    
    for j in range(data_processed.shape[1]):
        m, s = means[j], stds[j]
        mask = (data_processed[:, j] < m - n_sigma*s) | (data_processed[:, j] > m + n_sigma*s)
        data_processed[mask, j] = m
        
    return pd.DataFrame(data_processed, index=df_values.index)

# --- FUNZIONE LOGICA COLORI (GIALLO/ROSSO/VERDE) ---
def get_marker_colors(values):
    colors = []
    for v in values:
        if pd.isnull(v): colors.append('rgba(0,0,0,0)')
        elif abs(v) >= 5: colors.append('red')
        elif abs(v) >= 2: colors.append('orange')
        else: colors.append('green')
    return colors

# --- FUNZIONE ESPORTAZIONE EXCEL (Richiesta 5) ---
def export_to_excel_full(df_raw, l_barra, n_sigma):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. Bonifica Zeri per tutti i calcoli
        df_clean = df_raw.replace(0, np.nan)
        
        # Layer C (mm)
        df_c = l_barra * np.sin(np.radians(df_clean.values))
        df_c_out = pd.DataFrame(df_c, index=df_raw.index, columns=df_raw.columns)
        df_c_out.to_excel(writer, sheet_name='C')
        
        # Layer C0 (Delta Singolo)
        df_c0 = df_c_out - df_c_out.iloc[0, :]
        df_c0.to_excel(writer, sheet_name='C0')
        
        # Layer CP0 (Filtro Gauss e Soglie Allarme come VBA)
        df_cp0 = elaborazione_vba_originale(df_raw, l_barra, n_sigma)
        # Applicazione soglie (+20/-30) come in Modulo 1 VBA
        df_cp0[(df_cp0 > 20) | (df_cp0 < -30)] = np.nan
        df_cp0.to_excel(writer, sheet_name='CP0')
        
    return output.getvalue()

# --- FUNZIONE REPORT WORD (Richiesta 3 e 4) ---
def crea_report_word_avanzato(df_data, time_col, sensor_labels):
    doc = Document()
    doc.add_heading('Report Monitoraggio - Analisi Avanzata Trend', 0)
    
    for i, label in enumerate(sensor_labels):
        y_raw = df_data.iloc[:, i]
        
        # 4. Media Mobile su 5 punti (Richiesta 4)
        y_smooth = y_raw.rolling(window=5, center=True).mean() 
        
        plt.figure(figsize=(10, 4))
        # Visualizzazione Italiana Date (Richiesta 3)
        plt.plot(time_col, y_smooth, label='Media Mobile (5pt)', color='blue', linewidth=1.5)
        
        # 4. Trendline Polinomiale 3° Grado (Richiesta 4)
        valid = ~np.isnan(y_raw)
        if valid.any():
            x_num = np.arange(len(y_raw))
            z = np.polyfit(x_num[valid], y_raw[valid], 3)
            p = np.poly1d(z)
            plt.plot(time_col, p(x_num), '--', color='red', label='Trend Polinomiale', alpha=0.8)
            
        # 3. Titolo pulito senza diciture barrate (Richiesta 3)
        plt.title(f'Sensore: {label}') 
        plt.ylabel('mm')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.xticks(rotation=45)
        
        img_stream = BytesIO()
        plt.savefig(img_stream, format='png', bbox_inches='tight')
        doc.add_picture(img_stream, width=Inches(6.5))
        plt.close()
    
    out_word = BytesIO()
    doc.save(out_word)
    return out_word.getvalue()

# --- INTERFACCIA STREAMLIT ---
st.sidebar.header("⚙️ Parametri Elaborazione")
file_input = st.sidebar.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'])
asse_sel = st.sidebar.selectbox("Seleziona Asse", ["X", "Y", "Z"])
l_barra = st.sidebar.number_input("Lunghezza Barra (mm)", value=3000)
sigma_val = st.sidebar.slider("Filtro Gauss (Sigma)", 1.0, 4.0, 2.0)
limit_val = st.sidebar.number_input("Scala Grafico Y (mm)", value=30.0)
vel_animazione = st.sidebar.slider("Velocità Video (ms)", 100, 2000, 400)

if file_input:
    xls = pd.ExcelFile(file_input)
    sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info"] and not s.endswith(("C0", "C", "CP0"))]
    
    tab1, tab2 = st.tabs(["📊 Monitoraggio Dinamico", "🖨️ Generazione Report"])
    
    with tab1:
        sel_sheet = st.selectbox("Seleziona Layer Dati", sheets)
        df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df_full['Data e Ora'])
        
        sensor_cols = [c for c in df_full.columns if "CL_" in str(c) and f"_{asse_sel}" in str(c)]
        
        if sensor_cols:
            df_cp0 = elaborazione_vba_originale(df_full[sensor_cols], l_barra, sigma_val)
            labels = [re.search(r'CL_(\d+)', c).group(1) for c in sensor_cols]
            
            # --- GRAFICO DINAMICO ---
            st.subheader(f"🎬 Video Deformata - Asse {asse_sel} ({sel_sheet})")
            
            fig_vid = go.Figure()
            # Frame iniziale con colori dinamici
            fig_vid.add_trace(go.Scatter(
                x=labels, y=df_cp0.iloc[0],
                mode='lines+markers+text',
                text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_cp0.iloc[0]],
                textposition="top center",
                marker=dict(size=12, color=get_marker_colors(df_cp0.iloc[0]), line=dict(width=1, color='DarkSlateGrey'))
            ))

            fig_vid.update_layout(
                xaxis=dict(type='category', title="Sensori"),
                yaxis=dict(range=[-limit_val, limit_val], title="Spostamento (mm)"),
                height=600, template="plotly_white",
                sliders=[{
                    "active": 0,
                    "steps": [{"method": "animate", "label": t.strftime('%d/%m/%Y %H:%M'), 
                               "args": [[str(i)], {"frame": {"duration": vel_animazione, "redraw": True}}]} 
                              for i, t in enumerate(time_col)]
                }]
            )

            fig_vid.frames = [go.Frame(
                data=[go.Scatter(
                    x=labels, y=df_cp0.iloc[i],
                    text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_cp0.iloc[i]],
                    marker=dict(color=get_marker_colors(df_cp0.iloc[i]))
                )],
                name=str(i)
            ) for i in range(len(df_cp0))]
            
            st.plotly_chart(fig_vid, use_container_width=True)

    with tab2:
        st.subheader("Esportazione Documenti")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Genera Report Word (Stampe)"):
                word_data = crea_report_word_avanzato(df_cp0, time_col, labels)
                st.download_button("📥 Scarica Report .docx", word_data, f"Report_{sel_sheet}_{asse_sel}.docx")
        
        with col2:
            if st.button("📊 Genera File Excel Elaborato"):
                excel_data = export_to_excel_full(df_full[sensor_cols], l_barra, sigma_val)
                st.download_button("📥 Scarica Excel (C, C0, CP0)", excel_data, f"Elaborazione_{sel_sheet}.xlsx")

    st.sidebar.info("Il sistema applica automaticamente la Bonifica Zeri e il calcolo Delta Singolo conforme allo standard VBA.")
