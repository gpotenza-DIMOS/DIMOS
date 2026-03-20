import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os
from io import BytesIO

def run_elettrolivelle():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=300)
        
    st.title("📏 Modulo Elettrolivelle - Analisi Integrata")
    
    up = st.file_uploader("📂 Carica file Excel Elettrolivelle", type=['xlsx', 'xlsm'])
    
    if up:
        xls = pd.ExcelFile(up)
        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "NAME"]]
        sel_sheet = st.selectbox("Seleziona Sezione", sheets)
        
        with st.sidebar:
            st.header("🔧 Setup Algoritmo")
            asse = st.selectbox("Asse di analisi", ["X", "Y", "Z"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma = st.slider("Filtro Sigma (Gauss)", 1.0, 5.0, 2.5)
            
            st.divider()
            st.header("📈 Visualizzazione")
            tipo_grafico = st.radio("Tipo di calcolo", ["Spostamento Singolo", "Deformata Cumulata (Integrata)"])
            vel = st.slider("Velocità Animazione (ms)", 50, 1000, 200)
            limite_y = st.number_input("Range asse Y (+/- mm)", value=20.0)

        df = pd.read_excel(up, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df.iloc[:, 0])
        cols_asse = [c for c in df.columns if f"_{asse}" in str(c)]
        
        if cols_asse:
            # 1. TRASFORMAZIONE VETTORIALE
            data_raw = df[cols_asse].replace(0, np.nan).values
            data_mm = l_barra * np.sin(np.radians(data_raw))
            
            # 2. CALCOLO DELTA C0 (rispetto alla prima riga valida)
            first_valid = np.nanmean(data_mm[0:1, :], axis=0)
            data_c0 = data_mm - first_valid
            
            # 3. FILTRO OUTLIERS GAUSS
            m = np.nanmean(data_c0, axis=0)
            s = np.nanstd(data_c0, axis=0)
            data_c0[(data_c0 < m - sigma*s) | (data_c0 > m + sigma*s)] = np.nan
            
            # 4. CALCOLO DEFORMATA CUMULATA (Se selezionato)
            if tipo_grafico == "Deformata Cumulata (Integrata)":
                # Somma i mm di ogni sensore lungo la catena
                plot_data = np.nancumsum(data_c0, axis=1)
            else:
                plot_data = data_c0

            ids = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in cols_asse]

            # 5. COSTRUZIONE GRAFICO PLOTLY
            fig = go.Figure()
            
            # Aggiunta linea dello Zero
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

            # Traccia iniziale (Tempo 0)
            fig.add_trace(go.Scatter(
                x=ids, 
                y=plot_data[0], 
                mode='lines+markers+text',
                text=np.round(plot_data[0], 2), 
                textposition="top center",
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=10, color='red', symbol='square')
            ))
            
            # Generazione Frames per animazione
            frames = []
            for i in range(len(plot_data)):
                frames.append(go.Frame(
                    data=[go.Scatter(y=plot_data[i], text=np.round(plot_data[i], 2))],
                    name=str(i)
                ))
            
            fig.frames = frames
            
            fig.update_layout(
                title=f"{tipo_grafico} - Asse {asse}",
                yaxis=dict(title="Spostamento (mm)", range=[-limite_y, limite_y]),
                xaxis=dict(title="Posizione Sensori (Catena)"),
                template="plotly_white",
                updatemenus=[{
                    "buttons": [
                        {"args": [None, {"frame": {"duration": vel, "redraw": True}, "fromcurrent": True}],
                         "label": "▶ Play", "method": "animate"},
                        {"args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                         "label": "⏸ Pause", "method": "animate"}
                    ],
                    "type": "buttons", "direction": "left", "showactive": False, "x": 0.1, "y": 1.15
                }],
                sliders=[{
                    "steps": [
                        {"method": "animate", "label": time_col[i].strftime("%d/%m %H:%M"),
                         "args": [[str(i)], {"frame": {"duration": vel, "redraw": True}}]} 
                        for i in range(len(plot_data))
                    ],
                    "currentvalue": {"prefix": "Data: ", "font": {"size": 14}, "visible": True}
                }]
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 6. TABELLA MASSIMI (CON DOWNLOAD)
            st.subheader("📋 Analisi Statistica Sensori")
            res_df = pd.DataFrame({
                "ID Sensore": ids,
                "Spostamento Max (mm)": np.nanmax(plot_data, axis=0),
                "Spostamento Min (mm)": np.nanmin(plot_data, axis=0),
                "Ultima Lettura (mm)": plot_data[-1]
            }).round(3)
            
            st.dataframe(res_df, use_container_width=True)
            
            csv = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica Tabella CSV", csv, "riepilogo_livelle.csv", "text/csv")
            
        else:
            st.error(f"⚠️ Attenzione: Nessuna colonna trovata con suffisso _{asse}. Controlla il nome dei sensori nell'Excel.")
