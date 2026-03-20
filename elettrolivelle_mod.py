import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os
import matplotlib.pyplot as plt
from io import BytesIO

def run_elettrolivelle():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=300)
        
    st.title("📏 Analisi Avanzata Elettrolivelle")
    
    up = st.file_uploader("📂 Carica Excel Progetto", type=['xlsx', 'xlsm'])
    
    if up:
        xls = pd.ExcelFile(up)
        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "NAME", "Info"]]
        sel_sheet = st.selectbox("Seleziona Sezione di Monitoraggio", sheets)
        
        with st.sidebar:
            st.header("⚙️ Parametri Tecnici")
            asse = st.selectbox("Asse", ["X", "Y", "Z"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 2.5)
            st.divider()
            st.header("🎬 Controllo Animazione")
            vel = st.slider("Velocità (ms)", 50, 1000, 200)
            limite_y = st.number_input("Range Y (+/- mm)", value=15.0)

        df = pd.read_excel(up, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df.iloc[:, 0])
        cols_asse = [c for c in df.columns if f"_{asse}" in str(c)]
        
        if cols_asse:
            # --- MOTORE DI CALCOLO VETTORIALIZZATO ---
            data_raw = df[cols_asse].replace(0, np.nan).values
            data_mm = l_barra * np.sin(np.radians(data_raw))
            
            # Delta C0 rispetto alla prima riga valida (senza loop)
            first_valid = np.nanmean(data_mm[0:1, :], axis=0)
            data_c0 = data_mm - first_valid
            
            # Filtro Gauss
            if sigma > 0:
                m = np.nanmean(data_c0, axis=0)
                s = np.nanstd(data_c0, axis=0)
                data_c0[(data_c0 < m - sigma*s) | (data_c0 > m + sigma*s)] = np.nan
            
            df_final = pd.DataFrame(data_c0, columns=cols_asse, index=time_col)
            ids = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in cols_asse]

            # --- TABS DI VISUALIZZAZIONE ---
            tab_dinamico, tab_storico = st.tabs(["🎬 Deformata Dinamica", "📈 Analisi Temporale"])

            with tab_dinamico:
                st.subheader("Profilo della Struttura")
                tipo_v = st.radio("Modalità:", ["Spostamento Relativo", "Deformata Cumulata (Catena)"], horizontal=True)
                
                # Calcolo per la visualizzazione
                if "Cumulata" in tipo_v:
                    # Gestione nulli: riempiamo temporaneamente con 0 per la somma, 
                    # ma rimettiamo NaN dove il dato era assente
                    mask_nan = np.isnan(data_c0)
                    plot_vals = np.nancumsum(data_c0, axis=1)
                    plot_vals[mask_nan] = np.nan 
                else:
                    plot_vals = data_c0

                fig_vid = go.Figure()
                fig_vid.add_hline(y=0, line_color="black", line_width=1, opacity=0.3)
                
                # Traccia principale con PALLINI (Markers) e linee
                fig_vid.add_trace(go.Scatter(
                    x=ids, y=plot_vals[0],
                    mode='lines+markers+text',
                    text=[f"{v:.2f}" if pd.notnull(v) else "" for v in plot_vals[0]],
                    textposition="top center",
                    marker=dict(size=12, color='#ff4b4b', symbol='circle', line=dict(width=2, color="white")),
                    line=dict(color='#1f77b4', width=4),
                    connectgaps=False # Importante: non unisce i punti se c'è un nullo
                ))

                frames = [go.Frame(data=[go.Scatter(y=plot_vals[i], 
                          text=[f"{v:.2f}" if pd.notnull(v) else "" for v in plot_vals[i]])], 
                          name=str(i)) for i in range(len(plot_vals))]
                
                fig_vid.frames = frames
                fig_vid.update_layout(
                    yaxis=dict(range=[-limite_y, limite_y], title="Spostamento (mm)"),
                    xaxis=dict(title="ID Sensore (Posizione)"),
                    template="plotly_white",
                    sliders=[{"steps": [{"method": "animate", "label": time_col[i].strftime("%H:%M"),
                               "args": [[str(i)], {"frame": {"duration": vel, "redraw": False}}]} 
                               for i in range(len(plot_vals))]}],
                    updatemenus=[{"buttons": [{"args": [None, {"frame": {"duration": vel}}], "label": "Play", "method": "animate"},
                                              {"args": [[None], {"frame": {"duration": 0}}], "label": "Pausa", "method": "animate"}],
                                  "type": "buttons", "showactive": False, "x": 0, "y": 1.1}]
                )
                st.plotly_chart(fig_vid, use_container_width=True)

            with tab_storico:
                st.subheader("Evoluzione Temporale dei Sensori")
                sel_sens = st.multiselect("Scegli quali sensori confrontare:", options=cols_asse, default=cols_asse[:2])
                
                if sel_sens:
                    fig_time = go.Figure()
                    for s in sel_sens:
                        fig_time.add_trace(go.Scatter(x=time_col, y=df_final[s], name=s, mode='lines'))
                    
                    fig_time.update_layout(template="plotly_white", yaxis_title="mm", hovermode="x unified")
                    st.plotly_chart(fig_time, use_container_width=True)

            # --- SEZIONE REPORT (INTEGRATA) ---
            st.divider()
            if st.button("🚀 GENERA REPORT WORD ELETTROLIVELLE"):
                doc = Document()
                doc.add_heading(f'Monitoraggio Elettrolivelle: {sel_sheet}', 0)
                
                # Aggiungiamo un grafico della deformata finale al report
                plt.figure(figsize=(10, 5))
                plt.plot(ids, plot_vals[-1], marker='o', color='red', linestyle='-', linewidth=2)
                plt.axhline(0, color='black', lw=1)
                plt.title("Deformata all'ultima lettura")
                plt.grid(True)
                
                buf = BytesIO()
                plt.savefig(buf, format='png')
                doc.add_picture(buf, width=Inches(6))
                
                out = BytesIO()
                doc.save(out)
                st.download_button("⬇️ Scarica Report Elettrolivelle", out.getvalue(), f"Report_{sel_sheet}.docx")
