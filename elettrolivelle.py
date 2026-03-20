import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
from io import BytesIO

# --- LIBRERIE OPZIONALI ---
try:
    from docx import Document
    from docx.shared import Inches
    import plotly.io as pio
    DOC_OK = True
except:
    DOC_OK = False

# --- MOTORE DI CALCOLO (L*sin(rad), Delta C0, Cumulata CP0) ---
@st.cache_data(show_spinner=False)
def elaborazione_vba_originale(df_values, l_barra, n_sigma, limit_val):
    # 1. Calcolo mm
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    # 2. Delta C0
    data_c0 = data_mm - data_mm[0, :]
    # 3. Cumulata lungo la riga (CP0)
    data_cp0 = np.cumsum(data_c0, axis=1)
    
    # Filtro Limiti e Sigma
    data_cp0[np.abs(data_cp0) > limit_val] = np.nan
    means = np.nanmean(data_cp0, axis=0)
    stds = np.nanstd(data_cp0, axis=0)
    for j in range(data_cp0.shape[1]):
        m, s = means[j], stds[j]
        mask = (data_cp0[:, j] < m - n_sigma*s) | (data_cp0[:, j] > m + n_sigma*s) | (np.isnan(data_cp0[:, j]))
        data_cp0[mask, j] = m
    return pd.DataFrame(data_cp0, index=df_values.index).ffill().fillna(0)

# --- FUNZIONE PRINCIPALE RICHIAMATA DA APP_DIMOS ---
def run_elettrolivelle_advanced():
    st.header("📏 Modulo Elettrolivelle")

    with st.sidebar:
        st.divider()
        file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsm', 'xlsx'], key="el_up")
        if file_input:
            asse_sel = st.selectbox("Asse di Analisi", ["X", "Y", "Z"], key="el_asse")
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma_val = st.slider("Filtro Sigma", 1.0, 4.0, 2.0)
            limit_val = st.number_input("Soglia Errore (mm)", value=30.0)
            st.divider()
            step_v = st.select_slider("Campionamento Video:", options=["Ogni Lettura", "1 Giorno", "1 Settimana"], value="1 Giorno")
            vel_v = st.slider("Velocità (ms)", 100, 1000, 400)

    if not file_input:
        st.info("Carica il file Excel per visualizzare i grafici.")
        return

    xls = pd.ExcelFile(file_input)
    sheets = [s for s in xls.sheet_names if s.startswith("ETS_") and not s.endswith(("C0", "CP0"))]
    
    tab1, tab2 = st.tabs(["🎥 Video Deformata", "📄 Report Word"])

    with tab1:
        sel_s = st.selectbox("Seleziona Stringa", sheets)
        df = pd.read_excel(file_input, sheet_name=sel_s)
        df.columns = [str(c).strip() for c in df.columns]
        time_c = pd.to_datetime(df.iloc[:, 0])

        # Sequenza da foglio ARRAY
        s_order = []
        if "ARRAY" in xls.sheet_names:
            df_a = pd.read_excel(file_input, sheet_name="ARRAY", header=None)
            r = df_a[df_a[0] == sel_s]
            if not r.empty:
                s_order = r.iloc[0, 1:].dropna().astype(str).tolist()

        c_found, l_x = [], []
        for s_id in s_order:
            pat = rf"{s_id}.*_{asse_sel}"
            m = [c for c in df.columns if re.search(pat, str(c), re.IGNORECASE)]
            if m:
                c_found.append(m[0])
                l_x.append(s_id)

        if not c_found:
            st.error(f"Nessuna colonna per {asse_sel} in {sel_s}")
            return

        # Calcolo
        df_res = elaborazione_vba_originale(df[c_found].ffill(), l_barra, sigma_val, limit_val)
        
        # Campionamento
        df_res['DT'] = time_c
        if step_v == "1 Giorno": df_s = df_res.groupby(df_res['DT'].dt.date).first().drop(columns='DT')
        elif step_v == "1 Settimana": df_s = df_res.set_index('DT').resample('W').first().dropna()
        else: df_s = df_res.set_index('DT')

        # Plotly Animato
        fig = go.Figure(data=[go.Scatter(x=l_x, y=df_s.iloc[0], mode='lines+markers+text', text=[f"{v:.2f}" for v in df_s.iloc[0]], textposition="top center")])
        fig.update_layout(xaxis=dict(type='category', title="Sequenza"), yaxis=dict(range=[-limit_val-5, limit_val+5], title="mm"), template="plotly_white", height=600,
                          sliders=[{"steps": [{"method": "animate", "label": str(t), "args": [[str(i)], {"frame": {"duration": vel_v, "redraw": True}}]} for i, t in enumerate(df_s.index)]}])
        fig.frames = [go.Frame(data=[go.Scatter(x=l_x, y=df_s.iloc[i], text=[f"{v:.2f}" for v in df_s.iloc[i]], marker=dict(color=['red' if abs(v)>10 else 'green' for v in df_s.iloc[i]]))], name=str(i)) for i in range(len(df_s))]
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if st.button("🚀 GENERA REPORT"):
            if not DOC_OK: st.error("Librerie docx/pio mancanti.")
            else:
                doc = Document()
                doc.add_heading(f"Monitoraggio: {sel_s}", 0)
                img_buf = BytesIO()
                pio.write_image(fig, img_buf, format="png")
                doc.add_picture(img_buf, width=Inches(6))
                word_out = BytesIO()
                doc.save(word_out)
                st.download_button("📥 Scarica Report", word_out.getvalue(), f"Report_{sel_s}.docx")
