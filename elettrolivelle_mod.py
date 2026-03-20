import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# --- SUPPORTO REPORT ---
try:
    from docx import Document
    from docx.shared import Inches
    import plotly.io as pio
    DOC_SUPPORT = True
except:
    DOC_SUPPORT = False

# --- MOTORE DI CALCOLO IDENTICO A EXCEL/VBA ---
@st.cache_data(show_spinner=False)
def calcolo_deformata_fabro(df_values, l_barra, n_sigma, limit_val):
    # 1. Conversione Angolo -> mm (L * sin(rad))
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    # 2. Calcolo Delta C0 (Valore attuale - Prima lettura)
    data_c0 = data_mm - data_mm[0, :]
    # 3. Deformata Cumulata CP0 (Somma orizzontale sensori)
    data_cp0 = np.cumsum(data_c0, axis=1)
    
    # Filtri di pulizia (Sigma e Soglia)
    data_cp0[np.abs(data_cp0) > limit_val] = np.nan
    means = np.nanmean(data_cp0, axis=0)
    stds = np.nanstd(data_cp0, axis=0)
    for j in range(data_cp0.shape[1]):
        m, s = means[j], stds[j]
        if s > 0:
            mask = (data_cp0[:, j] < m - n_sigma*s) | (data_cp0[:, j] > m + n_sigma*s) | (np.isnan(data_cp0[:, j]))
            data_cp0[mask, j] = m
    return pd.DataFrame(data_cp0, index=df_values.index).ffill().fillna(0)

# --- QUESTA È LA FUNZIONE RICHIAMATA DA app_DIMOS.py ---
def run_elettrolivelle():
    st.markdown("### 📏 Analisi Deformate Elettrolivelle")

    with st.sidebar:
        st.divider()
        uploaded_file = st.file_uploader("Carica File Excel Fabro", type=['xlsm', 'xlsx'], key="up_el")
        if uploaded_file:
            asse = st.selectbox("Seleziona Asse", ["X", "Y", "Z"], key="sel_asse")
            L = st.number_input("Lunghezza Barra (mm)", value=3000)
            sig = st.slider("Filtro Sigma", 1.0, 4.0, 2.0)
            lim = st.number_input("Soglia Errore (mm)", value=30.0)
            st.divider()
            campionamento = st.select_slider("Frequenza Video:", options=["Tutte", "1 Giorno", "1 Settimana"], value="1 Giorno")
            fps = st.slider("Velocità Frame (ms)", 100, 1000, 400)

    if not uploaded_file:
        st.warning("⚠️ Carica il file Excel per visualizzare i dati.")
        return

    # Lettura fogli dati
    xls = pd.ExcelFile(uploaded_file)
    fogli_dati = [s for s in xls.sheet_names if s.startswith("ETS_") and not s.endswith(("C0", "CP0"))]
    
    tab_graf, tab_rep = st.tabs(["📈 Grafico Dinamico", "📄 Esportazione Report"])

    with tab_graf:
        stringa = st.selectbox("Seleziona Stringa Sensori", fogli_dati)
        df_raw = pd.read_excel(uploaded_file, sheet_name=stringa)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        date_series = pd.to_datetime(df_raw.iloc[:, 0])

        # Lettura Sequenza Fisica (Foglio ARRAY)
        ordine_fisico = []
        if "ARRAY" in xls.sheet_names:
            df_arr = pd.read_excel(uploaded_file, sheet_name="ARRAY", header=None)
            matching_row = df_arr[df_arr[0] == stringa]
            if not matching_row.empty:
                ordine_fisico = matching_row.iloc[0, 1:].dropna().astype(str).tolist()

        # Selezione colonne sensori
        col_ok, labels = [], []
        for s_id in ordine_fisico:
            regex = rf"{s_id}.*_{asse}"
            match = [c for c in df_raw.columns if re.search(regex, str(c), re.IGNORECASE)]
            if match:
                col_ok.append(match[0])
                labels.append(s_id)

        if not col_ok:
            st.error(f"Dati mancanti per l'asse {asse} nella stringa {stringa}.")
            return

        # Calcolo Deformata
        df_cp0 = calcolo_deformata_fabro(df_raw[col_ok].ffill(), L, sig, lim)
        
        # Campionamento temporale
        df_cp0['Data_Ora'] = date_series
        if campionamento == "1 Giorno":
            df_plot = df_cp0.groupby(df_cp0['Data_Ora'].dt.date).first().drop(columns='Data_Ora')
        elif campionamento == "1 Settimana":
            df_plot = df_cp0.set_index('Data_Ora').resample('W').first().dropna()
        else:
            df_plot = df_cp0.set_index('Data_Ora')

        # Creazione Plotly
        fig = go.Figure(data=[go.Scatter(x=labels, y=df_plot.iloc[0], mode='lines+markers+text', 
                                         text=[f"{v:.2f}" for v in df_plot.iloc[0]], textposition="top center")])
        
        fig.update_layout(xaxis=dict(type='category', title="Sensori (Ordine ARRAY)"),
                          yaxis=dict(range=[-lim-5, lim+5], title="Deformata (mm)"),
                          template="plotly_white", height=650,
                          sliders=[{"steps": [{"method": "animate", "label": str(t), 
                                   "args": [[str(i)], {"frame": {"duration": fps, "redraw": True}}]} 
                                  for i, t in enumerate(df_plot.index)]}])

        fig.frames = [go.Frame(data=[go.Scatter(x=labels, y=df_plot.iloc[i], 
                                               text=[f"{v:.2f}" for v in df_plot.iloc[i]],
                                               marker=dict(color=['red' if abs(v)>15 else 'green' for v in df_plot.iloc[i]]))], 
                               name=str(i)) for i in range(len(df_plot))]

        st.plotly_chart(fig, use_container_width=True)

    with tab_rep:
        if st.button("🚀 GENERA DOCUMENTO WORD"):
            if not DOC_SUPPORT:
                st.error("Librerie mancanti per il report.")
            else:
                doc = Document()
                doc.add_heading(f"Report Deformata - Stringa {stringa}", 0)
                img_stream = BytesIO()
                pio.write_image(fig, img_stream, format="png", width=1000, height=600)
                doc.add_picture(img_stream, width=Inches(6.5))
                target = BytesIO()
                doc.save(target)
                st.download_button("📥 Scarica Report", target.getvalue(), f"Report_{stringa}.docx")
