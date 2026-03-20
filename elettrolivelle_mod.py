import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os

# --- LOGICA SMART INTERPOLATION ---
def ricostruisci_dato_smart(serie, index_attuale, window=50):
    if not np.isnan(serie[index_attuale]):
        return serie[index_attuale], False
    
    start = max(0, index_attuale - window)
    finestra = serie[start:index_attuale]
    finestra_valida = finestra[~np.isnan(finestra)]
    
    if len(finestra_valida) < 5:
        return np.nan, False
    
    m = np.mean(finestra_valida)
    s = np.std(finestra_valida)
    dati_ottimali = finestra_valida[(finestra_valida >= m - s) & (finestra_valida <= m + s)]
    
    if len(dati_ottimali) > 0:
        return np.mean(dati_ottimali), True
    return np.nan, False

def run_elettrolivelle():
    st.header("📏 Monitoraggio Avanzato Elettrolivelle")
    
    with st.sidebar:
        st.header("⚙️ Parametri Modulo")
        file_input = st.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])
        asse = st.selectbox("Asse di Analisi", ["X", "Y", "Z"])
        l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
        sigma = st.slider("Filtro Sigma Gauss", 0.0, 5.0, 2.5)
        vel = st.slider("Velocità Video (ms)", 50, 1000, 200)
        limite_y = st.number_input("Range asse Y (+/- mm)", value=20.0)

    if file_input:
        xls = pd.ExcelFile(file_input)
        
        # 1. GESTIONE SEQUENZA ARRAY
        sequenza_fisica = None
        if "ARRAY" in xls.sheet_names:
            df_array = pd.read_excel(xls, sheet_name="ARRAY")
            sequenza_fisica = df_array.iloc[:, 0].dropna().astype(str).tolist()

        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "NAME", "Info"]]
        sel_sheet = st.selectbox("Seleziona Layer", sheets)
        
        df = pd.read_excel(file_input, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df.iloc[:, 0])
        cols_asse = [c for c in df.columns if f"_{asse}" in str(c)]
        
        # Ordinamento colonne secondo ARRAY
        if sequenza_fisica:
            def sort_key(c):
                for i, s in enumerate(sequenza_fisica):
                    if s in c: return i
                return 999
            cols_asse = sorted(cols_asse, key=sort_key)

        if cols_asse:
            # 2. ELABORAZIONE DATI
            data_raw = df[cols_asse].replace(0, np.nan).values
            data_mm = l_barra * np.sin(np.radians(data_raw))
            data_c0 = data_mm - np.nanmean(data_mm[0:1, :], axis=0)

            # Filtro Gauss
            if sigma > 0:
                m = np.nanmean(data_c0, axis=0)
                s = np.nanstd(data_c0, axis=0)
                data_c0[(data_c0 < m - sigma*s) | (data_c0 > m + sigma*s)] = np.nan

            # 3. SMART INTERPOLATION
            plot_vals = np.zeros_like(data_c0)
            is_ricostruito = np.zeros_like(data_c0, dtype=bool)
            for i in range(len(data_c0)):
                for j in range(len(cols_asse)):
                    val, ric = ricostruisci_dato_smart(data_c0[:, j], i)
                    plot_vals[i, j] = val
                    is_ricostruito[i, j] = ric

            tab_din, tab_storia = st.tabs(["🎬 Deformata Dinamica", "📈 Analisi Temporale"])

            with tab_din:
                tipo_v = st.radio("Modalità:", ["Spostamento Singolo", "Deformata Cumulata (Catena)"], horizontal=True)
                if "Cumulata" in tipo_v:
                    final_plot = np.nancumsum(plot_vals, axis=1)
                else:
                    final_plot = plot_vals

                ids = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in cols_asse]
                
                fig = go.Figure()
                fig.add_hline(y=0, line_dash="dash", line_color="gray")

                # Frame iniziale
                symbols = ["circle" if not r else "square" for r in is_ricostruito[0]]
                colors = ["red" if not r else "#00b4d8" for r in is_ricostruito[0]]
                
                fig.add_trace(go.Scatter(
                    x=ids, y=final_plot[0],
                    mode='lines+markers+text',
                    text=[f"!" if r else "" for r in is_ricostruito[0]],
                    textposition="middle center",
                    textfont=dict(color="white", size=10),
                    marker=dict(size=14, symbol=symbols, color=colors, line=dict(width=2, color="white")),
                    line=dict(width=3, color='#1f77b4'),
                    connectgaps=True
                ))

                # Frames animazione
                frames = [go.Frame(data=[go.Scatter(
                    y=final_plot[i],
                    marker=dict(symbol=["circle" if not r else "square" for r in is_ricostruito[i]],
                                color=["red" if not r else "#00b4d8" for r in is_ricostruito[i]]),
                    text=[f"!" if r else "" for r in is_ricostruito[i]]
                )], name=str(i)) for i in range(len(final_plot))]
                
                fig.frames = frames
                fig.update_layout(
                    yaxis=dict(range=[-limite_y, limite_y], title="mm"),
                    template="plotly_white",
                    updatemenus=[{"buttons": [{"args": [None, {"frame": {"duration": vel}}], "label": "Play", "method": "animate"}], "type": "buttons"}],
                    sliders=[{"steps": [{"method": "animate", "label": time_col[i].strftime("%H:%M"), "args": [[str(i)], {"frame": {"duration": vel}}]} for i in range(len(final_plot))]}]
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab_storia:
                sel_s = st.multiselect("Seleziona sensori:", cols_asse, default=cols_asse[:1])
                if sel_s:
                    fig_t = go.Figure()
                    for s in sel_s:
                        fig_t.add_trace(go.Scatter(x=time_col, y=pd.DataFrame(data_c0, columns=cols_asse)[s], name=s))
                    st.plotly_chart(fig_t, use_container_width=True)
    else:
        st.info("Carica un file Excel dalla sidebar per iniziare.")
