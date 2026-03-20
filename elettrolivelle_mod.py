import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from datetime import datetime
from io import BytesIO

try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- LOGICA VBA: COLORI ---
def get_vba_color(val):
    v = abs(val)
    if pd.isna(v): return "gray"
    if v <= 1: return "rgb(146, 208, 80)"
    if v <= 2: return "rgb(0, 176, 80)"
    if v <= 3: return "rgb(255, 255, 0)"
    if v <= 4: return "rgb(255, 192, 0)"
    if v <= 5: return "rgb(255, 0, 0)"
    return "rgb(112, 48, 160)"

# --- MOTORE DI CALCOLO (VBA MERGE) ---
def elaborazione_vba_style(df_values, l_barra, n_sigma):
    data = df_values.replace(0, np.nan).values
    data_mm = l_barra * np.sin(np.radians(data))
    # Delta C0 rispetto alla prima riga valida
    data_c0 = data_mm - np.nanmean(data_mm[0:1, :], axis=0)
    
    # Pulizia Gauss
    m_vec = np.nanmean(data_c0, axis=0)
    s_vec = np.nanstd(data_c0, axis=0)
    punti_gauss = 0
    for j in range(data_c0.shape[1]):
        mask = np.abs(data_c0[:, j] - m_vec[j]) > (s_vec[j] * n_sigma)
        punti_gauss += np.sum(mask)
        data_c0[mask, j] = np.nan
        
    # Soglie Hard VBA
    mask_soglie = (data_c0 > 20) | (data_c0 < -30)
    punti_soglie = np.sum(mask_soglie)
    data_c0[mask_soglie] = np.nan
    
    stats = f"Gauss ({n_sigma}σ): {punti_gauss} corr. | Soglie (+20/-30): {punti_soglie} elim."
    return data_c0, stats

def run_elettrolivelle():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    
    st.title("📏 Analisi Elettrolivelle (Sequenza ARRAY)")
    up = st.file_uploader("📂 Carica Excel", type=['xlsx', 'xlsm'])
    
    if up:
        xls = pd.ExcelFile(up)
        
        # --- 1. LETTURA SEQUENZA ARRAY (IL CUORE DEL SISTEMA) ---
        sequenza_fisica = []
        if "ARRAY" in xls.sheet_names:
            df_array = pd.read_excel(xls, sheet_name="ARRAY")
            # Legge la prima colonna del foglio ARRAY (es. CL_01, CL_02...)
            sequenza_fisica = df_array.iloc[:, 0].dropna().astype(str).tolist()
            st.success(f"✅ Sequenza ARRAY caricata: {len(sequenza_fisica)} sensori in ordine fisico.")
        else:
            st.warning("⚠️ Foglio ARRAY non trovato. L'ordine dei sensori sarà alfabetico.")

        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "NAME", "Info"]]
        sel_sheet = st.selectbox("Seleziona Sezione", sheets)
        
        with st.sidebar:
            st.header("⚙️ Configurazione")
            asse = st.selectbox("Asse", ["X", "Y", "Z"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma_val = st.slider("Sigma Gauss", 1.0, 5.0, 2.0)
            tipo_grafico = st.radio("Tipo Visualizzazione", ["Spostamenti Singoli", "Deformata Cumulata"])
            limite_y = st.number_input("Range Y (mm)", value=20.0)

        df = pd.read_excel(up, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df.iloc[:, 0])
        
        # --- 2. ORDINAMENTO SECONDO ARRAY (Logica InStr del VBA) ---
        cols_found = []
        if sequenza_fisica:
            for sensore in sequenza_fisica:
                # Cerca tra le colonne del foglio quella che contiene l'ID e l'asse (es. CL_01 e _X)
                match = [c for c in df.columns if sensore in str(c) and f"_{asse}" in str(c)]
                if match:
                    cols_found.append(match[0])
        else:
            cols_found = [c for c in df.columns if f"_{asse}" in str(c)]

        if cols_found:
            data_final, stats = elaborazione_vba_style(df[cols_found], l_barra, sigma_val)
            
            # Se Cumulata, sommiamo i valori lungo l'asse dei sensori (orizzontale)
            if tipo_grafico == "Deformata Cumulata":
                data_plot = np.nancumsum(data_final, axis=1)
            else:
                data_plot = data_final

            labels = [re.search(r'CL_(\d+)', c).group(0) if "CL_" in c else c for c in cols_found]

            tab1, tab2 = st.tabs(["🎬 Grafico Dinamico", "📄 Report Word"])

            with tab1:
                st.info(stats)
                idx = st.slider("Sposta nel tempo", 0, len(time_col)-1, len(time_col)-1)
                
                curr_vals = data_plot[idx]
                curr_colors = [get_vba_color(v) for v in data_final[idx]] # Colore sempre basato sul delta singolo
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=labels, y=curr_vals,
                    mode='lines+markers+text',
                    text=[f"{v:.2f}" if pd.notnull(v) else "" for v in curr_vals],
                    textposition="top center",
                    marker=dict(size=12, color=curr_colors, line=dict(width=1, color="black")),
                    line=dict(width=3, color="gray" if "Cumulata" in tipo_grafico else "#1f77b4")
                ))
                
                fig.update_layout(
                    title=f"Lettura: {time_col[idx]}",
                    yaxis=dict(range=[-limite_y, limite_y], title="Spostamento (mm)"),
                    xaxis=dict(tickangle=-90),
                    template="plotly_white", height=600
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                freq = st.selectbox("Frequenza Report:", ["Tutti i dati", "Giornaliero", "Settimanale"])
                if st.button("🚀 Genera Report Word"):
                    doc = Document()
                    doc.add_heading(f"Report {sel_sheet} - Asse {asse}", 0)
                    doc.add_paragraph(stats)
                    
                    # Campionamento
                    df_res = pd.DataFrame(data_plot, index=time_col)
                    if freq == "Giornaliero": df_res = df_res.resample('D').mean().dropna()
                    elif freq == "Settimanale": df_res = df_res.resample('W').mean().dropna()
                    
                    for d, row in df_res.iterrows():
                        plt.figure(figsize=(10, 4))
                        plt.plot(labels, row.values, marker='o', color='red')
                        plt.title(f"Data: {d.strftime('%d/%m/%Y')}")
                        plt.grid(True, alpha=0.3)
                        plt.ylim(-limite_y, limite_y)
                        plt.xticks(rotation=90)
                        
                        buf = BytesIO()
                        plt.savefig(buf, format='png', bbox_inches='tight')
                        doc.add_picture(buf, width=Inches(6))
                        plt.close()

                    out = BytesIO()
                    doc.save(out)
                    st.download_button("⬇️ Scarica Documento", out.getvalue(), "Report.docx")
        else:
            st.error("Nessun sensore trovato per l'asse selezionato.")
