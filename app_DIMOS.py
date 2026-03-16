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
    # 1. BONIFICA ZERI
    df_values = df_values.replace(0, np.nan)
    
    # Conversione gradi -> mm
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    
    # 2. DELTA SINGOLO (Rispetto a prima riga, no cumulata)
    data_c0 = data_mm - data_mm[0, :]
    
    # Filtraggio Outlier Sigma Gauss (Sostituzione con media come VBA)
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

# --- FUNZIONE ESPORTAZIONE EXCEL ---
def export_to_excel(df_raw, l_barra):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Layer C (mm)
        df_c = l_barra * np.sin(np.radians(df_raw.replace(0, np.nan)))
        df_c.to_excel(writer, sheet_name='C')
        # Layer C0 (Delta)
        df_c0 = df_c - df_c.iloc[0, :]
        df_c0.to_excel(writer, sheet_name='C0')
    return output.getvalue()

# --- FUNZIONE REPORT WORD ---
def crea_report_word(df_data, time_col, sensor_labels):
    doc = Document()
    doc.add_heading('Report Monitoraggio - Analisi Trend', 0)
    for i, label in enumerate(sensor_labels):
        y_raw = df_data.iloc[:, i]
        y_smooth = y_raw.rolling(window=5, center=True).mean() # Media Mobile 5pt
        
        plt.figure(figsize=(10, 4))
        plt.plot(time_col, y_smooth, label='Media Mobile (5pt)', color='blue')
        
        valid = ~np.isnan(y_raw)
        if valid.any():
            x_num = np.arange(len(y_raw))
            z = np.polyfit(x_num[valid], y_raw[valid], 3) # Trendline 3° grado
            p = np.poly1d(z)
            plt.plot(time_col, p(x_num), '--', color='red', label='Trend Polinomiale')
            
        plt.title(f'Sensore: {label}') # Titolo pulito
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        
        img_stream = BytesIO()
        plt.savefig(img_stream, format='png', bbox_inches='tight')
        doc.add_picture(img_stream, width=Inches(6))
        plt.close()
    
    out_word = BytesIO()
    doc.save(out_word)
    return out_word.getvalue()

# --- INTERFACCIA ---
st.sidebar.header("⚙️ Parametri")
file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])
asse_sel = st.sidebar.selectbox("Asse", ["X", "Y", "Z"])
l_barra = st.sidebar.number_input("Lunghezza Barra (mm)", value=3000)
sigma_val = st.sidebar.slider("Sigma Gauss", 1.0, 4.0, 2.0)
limit_val = st.sidebar.number_input("Limite Grafico (mm)", value=30.0)
vel_animazione = st.sidebar.slider("Velocità Video (ms)", 100, 2000, 400)

if file_input:
    xls = pd.ExcelFile(file_input)
    sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info"] and not s.endswith(("C0", "C"))]
    
    tab1, tab2 = st.tabs(["📊 Analisi Dinamica", "🖨️ Report Word"])
    
    with tab1:
        sel_sheet = st.selectbox("Seleziona Layer", sheets)
        df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df_full['Data e Ora'])
        
        # Identificazione sensori
        sensor_cols = [c for c in df_full.columns if "CL_" in str(c) and f"_{asse_sel}" in str(c)]
        
        if sensor_cols:
            df_cp0 = elaborazione_vba_originale(df_full[sensor_cols], l_barra, sigma_val)
            labels = [re.search(r'CL_(\d+)', c).group(1) for c in sensor_cols]
            
            # --- 3. GRAFICO DINAMICO (RIPRISTINATO) ---
            st.subheader(f"🎬 Animazione Deformata Asse {asse_sel}")
            
            fig_vid = go.Figure()
            # Frame iniziale
            fig_vid.add_trace(go.Scatter(
                x=labels, y=df_cp0.iloc[0],
                mode='lines+markers+text',
                text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_cp0.iloc[0]],
                textposition="top center",
                marker=dict(size=12, color=get_marker_colors(df_cp0.iloc[0]))
            ))

            # Configurazione Layout e Slider
            fig_vid.update_layout(
                xaxis=dict(type='category', title="ID Sensore"),
                yaxis=dict(range=[-limit_val, limit_val], title="Spostamento (mm)"),
                height=600, template="plotly_white",
                sliders=[{
                    "steps": [{"method": "animate", "label": t.strftime('%d/%m/%Y %H:%M'), 
                               "args": [[str(i)], {"frame": {"duration": vel_animazione, "redraw": True}}]} 
                              for i, t in enumerate(time_col)]
                }]
            )

            # Generazione Frame Animazione
            frames = [go.Frame(
                data=[go.Scatter(
                    x=labels, y=df_cp0.iloc[i],
                    text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_cp0.iloc[i]],
                    marker=dict(color=get_marker_colors(df_cp0.iloc[i]))
                )],
                name=str(i)
            ) for i in range(len(df_cp0))]
            
            fig_vid.frames = frames
            st.plotly_chart(fig_vid, use_container_width=True)

            # --- TREND TEMPORALE ---
            st.divider()
            st.subheader("📈 Trend Temporale")
            sel_s = st.multiselect("Seleziona Sensori", labels, default=labels[:1])
            if sel_s:
                fig_t = go.Figure()
                for s in sel_s:
                    idx = labels.index(s)
                    y = df_cp0.iloc[:, idx]
                    # Media Mobile
                    y_m = y.rolling(window=5, center=True).mean()
                    fig_t.add_trace(go.Scatter(x=time_col, y=y_m, name=f"CL_{s} (Media Mobile)"))
                    # Trendline
                    v = ~np.isnan(y)
                    if v.any():
                        z = np.polyfit(np.arange(len(y))[v], y[v], 3)
                        p = np.poly1d(z)
                        fig_t.add_trace(go.Scatter(x=time_col, y=p(np.arange(len(y))), name=f"Trend {s}", line=dict(dash='dash')))
                
                fig_t.update_layout(xaxis=dict(tickformat="%d/%m/%Y"), template="plotly_white")
                st.plotly_chart(fig_t, use_container_width=True)

    with tab2:
        st.subheader("Generazione Stampe")
        if st.button("Genera Report Word"):
            word_data = crea_report_word(df_cp0, time_col, labels)
            st.download_button("Scarica .docx", word_data, "Report.docx")
            
    # Bottone Esportazione Excel sempre disponibile nella sidebar
    st.sidebar.divider()
    if st.sidebar.button("Esporta Dati Elaborati (Excel)"):
        excel_out = export_to_excel(df_full[sensor_cols], l_barra)
        st.sidebar.download_button("Scarica .xlsx", excel_out, "Dati_Elaborati.xlsx")
