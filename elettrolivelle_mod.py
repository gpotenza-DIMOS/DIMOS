import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re
import os
from io import BytesIO
from datetime import datetime

# --- LIBRERIA WORD ---
try:
    from docx import Document
    from docx.shared import Inches
    WORD_OK = True
except:
    WORD_OK = False

# --- LOGICA COLORI ---
def get_vba_color(val):
    v = abs(val)
    if pd.isna(v): return "gray"
    if v <= 1: return "rgb(146, 208, 80)"
    if v <= 2: return "rgb(0, 176, 80)"
    if v <= 3: return "rgb(255, 255, 0)"
    if v <= 4: return "rgb(255, 192, 0)"
    if v <= 5: return "rgb(255, 0, 0)"
    return "rgb(112, 48, 160)"

def run_elettrolivelle():
    st.title("📏 Sistema Integrato Elettrolivelle")
    
    up = st.file_uploader("Carica Excel Fabro", type=['xlsm', 'xlsx'])
    
    if up:
        xls = pd.ExcelFile(up)
        
        # 1. ANALISI ARRAY (SEQUENZA FISICA)
        if "ARRAY" not in xls.sheet_names:
            st.error("Manca il foglio 'ARRAY'.")
            return
        
        df_array = pd.read_excel(xls, "ARRAY", header=None)
        linee_nomi = df_array[0].dropna().unique().tolist()
        
        # 2. INTERFACCIA SELEZIONE
        col1, col2, col3 = st.columns(3)
        with col1:
            sel_linea = st.selectbox("Linea", linee_nomi)
        with col2:
            asse = st.selectbox("Asse", ["X", "Y"])
        with col3:
            tipo_calc = st.radio("Visualizza", ["Spostamenti", "Cumulata"], horizontal=True)

        # Estrazione sequenza ordinata
        sequenza = df_array[df_array[0] == sel_linea].iloc[0, 1:].dropna().astype(str).tolist()

        # 3. IDENTIFICAZIONE FOGLIO DATI (ETS_1, ETS_2...)
        df_raw = None
        for sn in xls.sheet_names:
            if sn.startswith("ETS_") and len(sn) <= 6: # Evita ETS_1X etc.
                temp = pd.read_excel(xls, sn)
                if any(str(sequenza[0]) in str(c) for c in temp.columns):
                    df_raw = temp
                    break
        
        if df_raw is not None:
            time_col = pd.to_datetime(df_raw.iloc[:, 0])
            
            # --- MOTORE DI CALCOLO ---
            with st.sidebar:
                st.header("Parametri VBA")
                l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
                sigma = st.slider("Gauss (Sigma)", 1.0, 5.0, 2.0)
                range_y = st.number_input("Range Y (+/- mm)", value=20.0)

            elaborati = []
            for s_id in sequenza:
                # Cerca colonna: deve contenere ID (es. CL_01) e ASSE (es. _X)
                pattern = rf"{s_id}.*_{asse}"
                col = [c for c in df_raw.columns if re.search(pattern, str(c), re.IGNORECASE)]
                
                if col:
                    # VBA logic: Rad -> Sin * L
                    vals = l_barra * np.sin(np.radians(df_raw[col[0]].replace(0, np.nan)))
                    # C0: Delta rispetto alla prima riga
                    delta = vals - vals.iloc[0]
                    # Filtro Gauss
                    m, s = delta.mean(), delta.std()
                    delta = delta.mask(np.abs(delta - m) > (s * sigma))
                    # Filtro Soglie
                    delta = delta.mask((delta > 20) | (delta < -30))
                    elaborati.append(delta)
                else:
                    elaborati.append(pd.Series([np.nan]*len(df_raw)))

            df_final = pd.concat(elaborati, axis=1)
            df_final.columns = sequenza

            if tipo_calc == "Cumulata":
                df_plot = df_final.cumsum(axis=1)
            else:
                df_plot = df_final

            # --- GRAFICO INTERATTIVO ---
            idx = st.slider("Data Lettura", 0, len(time_col)-1, len(time_col)-1)
            curr_time = time_col.iloc[idx]
            
            fig = go.Figure()
            y_vals = df_plot.iloc[idx]
            # Colore basato sempre sullo spostamento del singolo sensore (df_final)
            colors = [get_vba_color(v) for v in df_final.iloc[idx]]

            fig.add_trace(go.Scatter(
                x=sequenza, y=y_vals,
                mode='lines+markers+text',
                text=[f"{v:.2f}" if pd.notnull(v) else "" for v in y_vals],
                textposition="top center",
                marker=dict(size=12, color=colors, line=dict(width=1, color="black")),
                line=dict(color="gray", width=2)
            ))
            
            fig.update_layout(
                title=f"Analisi {sel_linea} - {curr_time.strftime('%d/%m/%Y %H:%M')}",
                yaxis=dict(range=[-range_y, range_y], title="mm"),
                template="plotly_white", height=600
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- SEZIONE STAMPE ---
            st.divider()
            st.subheader("📝 Generazione Report Word")
            c1, c2 = st.columns(2)
            with c1:
                freq = st.selectbox("Campionamento Report", ["Giornaliero", "Settimanale", "Tutti i dati"])
            
            if st.button("🚀 GENERA REPORT COMPLETO"):
                if not WORD_OK:
                    st.error("Errore: libreria Word non disponibile.")
                else:
                    doc = Document()
                    doc.add_heading(f"Report {sel_linea} - Asse {asse}", 0)
                    
                    df_rep = df_plot.copy()
                    df_rep.index = time_col
                    if freq == "Giornaliero": df_rep = df_rep.resample('D').mean().dropna(how='all')
                    elif freq == "Settimanale": df_rep = df_rep.resample('W').mean().dropna(how='all')

                    prog = st.progress(0)
                    for i, (d, row) in enumerate(df_rep.iterrows()):
                        plt.figure(figsize=(10, 4))
                        plt.plot(sequenza, row.values, marker='o', color='red')
                        plt.axhline(0, color='black', alpha=0.3)
                        plt.title(f"Lettura: {d.strftime('%d/%m/%Y')}")
                        plt.ylim(-range_y, range_y)
                        plt.xticks(rotation=45)
                        plt.grid(True, alpha=0.2)
                        
                        b = BytesIO()
                        plt.savefig(b, format='png', bbox_inches='tight')
                        plt.close()
                        doc.add_picture(b, width=Inches(6))
                        prog.progress((i+1)/len(df_rep))
                    
                    final_b = BytesIO()
                    doc.save(final_b)
                    st.download_button("💾 Scarica Word", final_b.getvalue(), f"Report_{sel_linea}.docx")

        else:
            st.error("Non trovo fogli ETS compatibili con la linea selezionata.")
