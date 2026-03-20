import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re
import os
from io import BytesIO
from datetime import datetime

try:
    from docx import Document
    from docx.shared import Inches
except ImportError:
    pass

def get_vba_color(val):
    v = abs(val)
    if pd.isna(v): return "gray"
    if v <= 1: return "rgb(146, 208, 80)"   # Verde 1
    if v <= 2: return "rgb(0, 176, 80)"     # Verde 2
    if v <= 3: return "rgb(255, 255, 0)"   # Giallo
    if v <= 4: return "rgb(255, 192, 0)"   # Arancio
    if v <= 5: return "rgb(255, 0, 0)"     # Rosso
    return "rgb(112, 48, 160)"              # Viola

def run_elettrolivelle():
    st.title("📏 Analisi Elettrolivelle (VBA Sync)")
    
    up = st.file_uploader("Carica il file Excel (es. Fabro...)", type=['xlsm', 'xlsx'])
    
    if up:
        xls = pd.ExcelFile(up)
        
        # 1. CARICAMENTO SEQUENZA DA FOGLIO ARRAY
        if "ARRAY" not in xls.sheet_names:
            st.error("Errore: Manca il foglio 'ARRAY' fondamentale per l'ordine dei sensori.")
            return
        
        df_array = pd.read_excel(xls, "ARRAY", header=None)
        linee_disponibili = df_array[0].dropna().unique().tolist()
        
        sel_linea = st.selectbox("Seleziona Linea (da ARRAY)", linee_disponibili)
        
        # Estraiamo i sensori per quella specifica riga della linea
        sensori_linea = df_array[df_array[0] == sel_linea].iloc[0, 1:].dropna().astype(str).tolist()
        
        # 2. SELEZIONE ASSE E PARAMETRI
        with st.sidebar:
            asse = st.selectbox("Asse", ["X", "Y"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma_val = st.slider("Gauss Sigma", 1.0, 4.0, 2.0)
            limite_y = st.number_input("Scala Grafico (+/- mm)", value=20.0)

        # 3. RICERCA DATI NEI FOGLI ETS_X
        # Cerchiamo in quale foglio ETS_ (1,2,3,4) si trovano i dati per la linea scelta
        df_dati = None
        for s_name in ["ETS_1", "ETS_2", "ETS_3", "ETS_4"]:
            if s_name in xls.sheet_names:
                temp_df = pd.read_excel(xls, s_name)
                # Verifica se almeno un sensore della linea è presente nelle colonne
                if any(sens in col for col in temp_df.columns for sens in sensori_linea):
                    df_dati = temp_df
                    break
        
        if df_dati is not None:
            time_col = pd.to_datetime(df_dati.iloc[:, 0]) # Colonna A (Date)
            
            # Identificazione colonne esatte (ID + ASSE)
            cols_selezionate = []
            for s_id in sensori_linea:
                pattern = f"{s_id}.*_{asse}"
                match = [c for c in df_dati.columns if re.search(pattern, str(c), re.IGNORECASE)]
                if match:
                    cols_selezionate.append(match[0])

            if not cols_selezionate:
                st.warning(f"Nessun dato trovato per l'asse {asse} nella linea {sel_linea}")
                return

            # --- CALCOLI (MERGE VBA) ---
            raw_data = df_dati[cols_selezionate].replace(0, np.nan)
            
            # VBA: L * Sin(v * PI / 180)
            data_mm = l_barra * np.sin(np.radians(raw_data.values))
            
            # VBA C0: Sottrazione della prima riga valida (riferimento zero)
            data_c0 = data_mm - data_mm[0, :]
            
            # VBA Gauss: 2 Sigma
            m_vec = np.nanmean(data_c0, axis=0)
            s_vec = np.nanstd(data_c0, axis=0)
            for j in range(data_c0.shape[1]):
                mask = np.abs(data_c0[:, j] - m_vec[j]) > (s_vec[j] * sigma_val)
                data_c0[mask, j] = np.nan
            
            # VBA Soglia: +20/-30
            data_c0[(data_c0 > 20) | (data_c0 < -30)] = np.nan

            # --- VISUALIZZAZIONE ---
            idx = st.slider("Seleziona Lettura", 0, len(time_col)-1, len(time_col)-1)
            
            current_vals = data_c0[idx]
            colors = [get_vba_color(v) for v in current_vals]
            
            fig = go.Figure()
            # La Spezzata
            fig.add_trace(go.Scatter(
                x=sensori_linea, y=current_vals,
                mode='lines+markers+text',
                text=[f"{v:.2f}" if pd.notnull(v) else "" for v in current_vals],
                textposition="top center",
                marker=dict(size=12, color=colors, line=dict(width=1, color="black")),
                line=dict(color="gray", width=2)
            ))
            
            fig.update_layout(
                title=f"Linea {sel_linea} - Data: {time_col[idx]}",
                yaxis=dict(range=[-limite_y, limite_y], title="mm"),
                xaxis=dict(title="Sequenza ARRAY", tickangle=-45),
                template="plotly_white", height=500
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- EXPORT WORD CAMPIONATO ---
            st.divider()
            st.subheader("🖨️ Export Report Word")
            freq = st.selectbox("Esporta un campione ogni:", ["Giorno", "Settimana", "Mese", "Tutti"])
            
            if st.button("Genera Documento Word"):
                doc = Document()
                doc.add_heading(f"Report Monitoraggio: {sel_linea}", 0)
                
                # Resampling temporale
                df_temp = pd.DataFrame(data_c0, index=time_col)
                if freq == "Giorno": df_res = df_temp.resample('D').mean().dropna(how='all')
                elif freq == "Settimana": df_res = df_temp.resample('W').mean().dropna(how='all')
                elif freq == "Mese": df_res = df_temp.resample('M').mean().dropna(how='all')
                else: df_res = df_temp
                
                prog = st.progress(0)
                for i, (date, row) in enumerate(df_res.iterrows()):
                    plt.figure(figsize=(10, 4))
                    plt.plot(sensori_linea, row.values, marker='o', color='red')
                    plt.axhline(0, color='black', linewidth=0.5)
                    plt.title(f"Data: {date.strftime('%d/%m/%Y')}")
                    plt.ylim(-limite_y, limite_y)
                    plt.grid(True, alpha=0.3)
                    
                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    plt.close()
                    doc.add_picture(buf, width=Inches(6))
                    doc.add_paragraph(f"Analisi del {date.strftime('%d/%m/%Y')}")
                    prog.progress((i+1)/len(df_res))
                
                final_buf = BytesIO()
                doc.save(final_buf)
                st.download_button("Scarica Report Word", final_buf.getvalue(), f"Report_{sel_linea}.docx")

        else:
            st.error("Non è stato possibile mappare i sensori di ARRAY sui fogli ETS_1...4. Controlla i nomi delle colonne.")
