import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from datetime import datetime, timedelta
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- LOGICA VBA: PULIZIA E SOGLIE ---
def elaborazione_vba_style(df_values, l_barra, n_sigma):
    # 1. Bonifica Zeri (VBA: If cella.Value = 0 Then ClearContents)
    data = df_values.replace(0, np.nan).values
    
    # 2. Conversione Trigonometrica (VBA: L * Sin(v * PI / 180))
    data_mm = l_barra * np.sin(np.radians(data))
    
    # 3. Calcolo C0 (Delta rispetto alla prima lettura valida riga 2 del VBA)
    # Cerchiamo la prima riga non completamente nulla per ogni colonna
    first_valid = np.nanmean(data_mm[0:1, :], axis=0)
    data_c0 = data_mm - first_valid
    
    # 4. Pulizia Gauss 2 Sigma (VBA: RiordinaEGeneraLayerX)
    report = []
    tot_punti = data_c0.size
    punti_corretti_gauss = 0
    
    m_vec = np.nanmean(data_c0, axis=0)
    s_vec = np.nanstd(data_c0, axis=0)
    
    for j in range(data_c0.shape[1]):
        mask = np.abs(data_c0[:, j] - m_vec[j]) > (s_vec[j] * n_sigma)
        punti_corretti_gauss += np.sum(mask)
        data_c0[mask, j] = np.nan # VBA metteva la media, noi mettiamo NaN per Smart Interp
        
    # 5. Soglie Hard (VBA: +20 / -30)
    mask_soglie = (data_c0 > 20) | (data_c0 < -30)
    punti_eliminati_soglie = np.sum(mask_soglie)
    data_c0[mask_soglie] = np.nan
    
    stat_text = (f"Punti corretti Gauss ({n_sigma}σ): {punti_corretti_gauss}\n"
                 f"Punti eliminati soglie (+20/-30): {punti_eliminati_soglie}\n"
                 f"Totale campioni analizzati: {tot_punti}")
    
    return data_c0, stat_text

# --- LOGICA VBA: COLORI (Select Case valAbs) ---
def get_vba_color(val):
    v = abs(val)
    if pd.isna(v): return "gray"
    if v <= 1: return "rgb(146, 208, 80)"   # Verde chiaro
    if v <= 2: return "rgb(0, 176, 80)"     # Verde scuro
    if v <= 3: return "rgb(255, 255, 0)"   # Giallo
    if v <= 4: return "rgb(255, 192, 0)"   # Arancione
    if v <= 5: return "rgb(255, 0, 0)"     # Rosso
    return "rgb(112, 48, 160)"              # Viola

def run_elettrolivelle():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    
    st.title("📏 Analisi Elettrolivelle (VBA Integrated)")
    
    up = st.file_uploader("📂 Carica Excel Progetto", type=['xlsx', 'xlsm'])
    
    if up:
        xls = pd.ExcelFile(up)
        
        # Sequenza ARRAY
        sequenza_fisica = None
        if "ARRAY" in xls.sheet_names:
            df_array = pd.read_excel(xls, sheet_name="ARRAY")
            sequenza_fisica = df_array.iloc[:, 0].dropna().astype(str).tolist()

        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "NAME", "Info"]]
        sel_sheet = st.selectbox("Seleziona Sezione", sheets)
        
        with st.sidebar:
            st.header("⚙️ Parametri VBA")
            asse = st.selectbox("Asse", ["X", "Y", "Z"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma_val = st.slider("Sigma Gauss", 1.0, 5.0, 2.0)
            st.divider()
            vel = st.slider("Velocità Animazione (ms)", 50, 1000, 200)
            limite_y = st.number_input("Limite Y Grafici (mm)", value=20.0)

        df = pd.read_excel(up, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df.iloc[:, 0])
        cols_asse = [c for c in df.columns if f"_{asse}" in str(c)]
        
        if sequenza_fisica:
            def sort_key(c):
                for i, s in enumerate(sequenza_fisica):
                    if s in c: return i
                return 999
            cols_asse = sorted(cols_asse, key=sort_key)

        if cols_asse:
            # ELABORAZIONE
            data_final, stats = elaborazione_vba_style(df[cols_asse], l_barra, sigma_val)
            ids = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in cols_asse]

            tab1, tab2 = st.tabs(["🎬 Dashboard Dinamica", "📄 Export Report Word"])

            with tab1:
                st.info(stats)
                idx = st.slider("Seleziona Istante Temporale", 0, len(time_col)-1, 0)
                
                # Calcolo colori per l'istante selezionato
                current_vals = data_final[idx]
                colors = [get_vba_color(v) for v in current_vals]
                
                fig = go.Figure()
                fig.add_hline(y=0, line_color="black", opacity=0.3)
                
                # La Spezzata
                fig.add_trace(go.Scatter(
                    x=ids, y=current_vals,
                    mode='lines+markers+text',
                    text=[f"{v:.2f}" if pd.notnull(v) else "NaN" for v in current_vals],
                    textposition="top center",
                    textfont=dict(size=9, color="black"),
                    marker=dict(size=12, color=colors, line=dict(width=1, color="white"), symbol="circle"),
                    line=dict(color="#1f77b4", width=3),
                    name=time_col[idx].strftime("%d/%m/%Y %H:%M")
                ))
                
                # Etichette sensori sotto i pallini (ruotate come VBA)
                fig.update_layout(
                    title=f"Data: {time_col[idx].strftime('%d/%m/%Y %H:%M:%S')}",
                    yaxis=dict(range=[-limite_y, limite_y], title="Spostamento (mm)"),
                    xaxis=dict(tickangle=-90, title="Sensori (Sequenza ARRAY)"),
                    template="plotly_white", height=600
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Configurazione Stampe")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 1. Report Statistico")
                    st.write("Genera un documento con i log di pulizia VBA e soglie.")
                    if st.button("Genera Report Statistico"):
                        doc = Document()
                        doc.add_heading("REPORT ELABORAZIONE ELETTROLIVELLE", 0)
                        doc.add_paragraph(stats)
                        buf = BytesIO()
                        doc.save(buf)
                        st.download_button("Scarica Statistiche", buf.getvalue(), "Stats_VBA.docx")

                with col2:
                    st.markdown("### 2. Report Spezzate Temporali")
                    freq = st.selectbox("Campionamento:", ["Giornaliero", "Settimanale", "Mensile", "Tutti i dati"])
                    
                    if st.button("Genera Report Grafici"):
                        # Logica di campionamento
                        df_temp = pd.DataFrame(data_final, index=time_col)
                        if freq == "Giornaliero": df_res = df_temp.resample('D').mean()
                        elif freq == "Settimanale": df_res = df_temp.resample('W').mean()
                        elif freq == "Mensile": df_res = df_temp.resample('M').mean()
                        else: df_res = df_temp

                        doc = Document()
                        doc.add_heading(f"Sequenza Deformate - {sel_sheet}", 0)
                        
                        progress_bar = st.progress(0)
                        for i, (date, row) in enumerate(df_res.iterrows()):
                            plt.figure(figsize=(10, 4))
                            plt.plot(ids, row.values, marker='o', color='red', linewidth=2)
                            plt.axhline(0, color='black', alpha=0.3)
                            plt.title(f"Data: {date.strftime('%d/%m/%Y')}")
                            plt.ylim(-limite_y, limite_y)
                            plt.grid(True, alpha=0.3)
                            
                            img_buf = BytesIO()
                            plt.savefig(img_buf, format='png')
                            plt.close()
                            doc.add_picture(img_buf, width=Inches(6))
                            doc.add_paragraph(f"Lettura del {date}")
                            progress_bar.progress((i + 1) / len(df_res))
                        
                        out = BytesIO()
                        doc.save(out)
                        st.download_button("Scarica Report Grafici", out.getvalue(), "Report_Spezzate.docx")

    else:
        st.info("In attesa del file Excel...")
