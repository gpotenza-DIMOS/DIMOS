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
        
    st.title("📏 Modulo Elettrolivelle - Analisi Sequenziale")
    
    # Caricamento file in pagina principale
    up = st.file_uploader("📂 Carica file Excel (con foglio ARRAY)", type=['xlsx', 'xlsm'])
    
    if up:
        xls = pd.ExcelFile(up)
        
        # 1. LOGICA SEQUENZA ARRAY
        if "ARRAY" in xls.sheet_names:
            df_array = pd.read_excel(xls, sheet_name="ARRAY")
            # Assumiamo che la sequenza sia definita nella prima colonna utile dell'ARRAY
            sequenza_fisica = df_array.iloc[:, 0].dropna().astype(str).tolist()
        else:
            st.warning("⚠️ Foglio 'ARRAY' non trovato. La sequenza sarà basata sull'ordine delle colonne.")
            sequenza_fisica = None

        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "NAME", "Info"]]
        sel_sheet = st.selectbox("Seleziona Sezione", sheets)
        
        with st.sidebar:
            st.header("⚙️ Parametri")
            asse = st.selectbox("Asse di analisi", ["X", "Y", "Z"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma = st.slider("Filtro Sigma", 0.0, 5.0, 2.5)
            st.divider()
            vel = st.slider("Velocità (ms)", 50, 1000, 200)
            limite_y = st.number_input("Range asse Y (+/- mm)", value=20.0)

        df = pd.read_excel(up, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df.iloc[:, 0])
        
        # Filtro colonne per ASSE
        cols_asse = [c for c in df.columns if f"_{asse}" in str(c)]
        
        # Ordinamento colonne in base alla sequenza ARRAY (se esiste)
        if sequenza_fisica:
            # Ordiniamo cols_asse seguendo l'ordine di apparizione in sequenza_fisica
            def sort_key(c):
                for i, s in enumerate(sequenza_fisica):
                    if s in c: return i
                return 999
            cols_asse = sorted(cols_asse, key=sort_key)

        if cols_asse:
            # --- CALCOLO VETTORIALIZZATO ---
            data_raw = df[cols_asse].replace(0, np.nan).values
            data_mm = l_barra * np.sin(np.radians(data_raw))
            
            # Calcolo Delta C0 rispetto alla prima riga
            first_row = np.nanmean(data_mm[0:1, :], axis=0)
            data_c0 = data_mm - first_row
            
            # Filtro Gauss
            if sigma > 0:
                m = np.nanmean(data_c0, axis=0)
                s = np.nanstd(data_c0, axis=0)
                data_c0[(data_c0 < m - sigma*s) | (data_c0 > m + sigma*s)] = np.nan
            
            ids_grafico = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in cols_asse]

            tab1, tab2 = st.tabs(["🎬 Profilo Strutturale", "📈 Storico Sensori"])

            with tab1:
                tipo_calc = st.radio("Visualizza:", ["Spostamento Singolo Tratto", "Deformata Cumulata (Catena)"], horizontal=True)
                
                if "Cumulata" in tipo_calc:
                    # Somma progressiva seguendo l'ordine dell'ARRAY
                    plot_vals = np.nancumsum(data_c0, axis=1)
                else:
                    plot_vals = data_c0

                fig = go.Figure()
                fig.add_hline(y=0, line_color="gray", opacity=0.5)
                
                # Traccia con PALLINI (Markers)
                fig.add_trace(go.Scatter(
                    x=ids_grafico, y=plot_vals[0],
                    mode='lines+markers',
                    marker=dict(size=12, color='red', symbol='circle', line=dict(width=2, color='white')),
                    line=dict(width=3, color='#1f77b4'),
                    connectgaps=False # Rispetta i valori nulli/vuoti
                ))

                # Frames animazione
                frames = [go.Frame(data=[go.Scatter(y=plot_vals[i])], name=str(i)) for i in range(len(plot_vals))]
                fig.frames = frames
                
                fig.update_layout(
                    yaxis=dict(range=[-limite_y, limite_y], title="mm"),
                    xaxis=dict(title="Sequenza Sensori (da ARRAY)"),
                    template="plotly_white",
                    updatemenus=[{"buttons": [{"args": [None, {"frame": {"duration": vel}}], "label": "Play", "method": "animate"}], "type": "buttons"}],
                    sliders=[{"steps": [{"method": "animate", "label": time_col[i].strftime("%H:%M"), "args": [[str(i)], {"frame": {"duration": vel}}]} for i in range(len(plot_vals))]}]
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                sel_s = st.multiselect("Seleziona sensori per grafico temporale:", cols_asse, default=cols_asse[:1])
                if sel_s:
                    df_temp = pd.DataFrame(data_c0, columns=cols_asse, index=time_col)
                    fig_t = go.Figure()
                    for s in sel_s:
                        fig_t.add_trace(go.Scatter(x=time_col, y=df_temp[s], name=s))
                    fig_t.update_layout(template="plotly_white", yaxis_title="mm")
                    st.plotly_chart(fig_t, use_container_width=True)
