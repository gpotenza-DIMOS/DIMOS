import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="DIMOS - Monitoraggio Avanzato", layout="wide")

# --- GESTIONE LOGHI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_asset_path(filename):
    return os.path.join(BASE_DIR, filename)

# --- SISTEMA DI AUTENTICAZIONE ---
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    if st.session_state["auth"]:
        return True

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        p_dimos = get_asset_path("logo_dimos.jpg")
        if os.path.exists(p_dimos):
            st.image(p_dimos, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Accesso</h2>", unsafe_allow_html=True)
        user_id = st.text_input("ID Utente")
        password = st.text_input("Password", type="password")
        if st.button("Entra"):
            if user_id == "dimos" and password == "micai!":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenziali errate.")
    return False

# --- MOTORE DI CALCOLO ---
@st.cache_data(show_spinner=False)
def elaborazione_vba_originale(df_values, l_barra, n_sigma, limit_val):
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    data_c0 = data_mm - data_mm[0, :]
    data_cp0 = np.cumsum(data_c0, axis=1)
    data_cp0[np.abs(data_cp0) > limit_val] = np.nan
    means = np.nanmean(data_cp0, axis=0)
    stds = np.nanstd(data_cp0, axis=0)
    for j in range(data_cp0.shape[1]):
        m, s = means[j], stds[j]
        mask = (data_cp0[:, j] < m - n_sigma*s) | (data_cp0[:, j] > m + n_sigma*s) | (np.isnan(data_cp0[:, j]))
        data_cp0[mask, j] = m
    return pd.DataFrame(data_cp0, index=df_values.index).ffill().bfill().fillna(0)

# --- ESECUZIONE ---
if check_password():
    p_main_logo = get_asset_path("logo_dimos.jpg")
    if os.path.exists(p_main_logo):
        st.image(p_main_logo, width=400)

    with st.sidebar:
        p_micro = get_asset_path("logo_microgeo.jpg") 
        if os.path.exists(p_micro): 
            st.image(p_micro, use_container_width=True)
        file_input = st.file_uploader("Carica Excel", type=['xls', 'xlsx', 'xlsm'])
        asse_sel = st.selectbox("Asse", ["X", "Y", "Z"])
        l_barra = st.number_input("Lunghezza (mm)", value=3000)
        sigma_val = st.slider("Sigma (σ)", 1.0, 4.0, 2.0)
        limit_val = st.number_input("Limiti (mm)", value=30.0)

    if file_input:
        xls = pd.ExcelFile(file_input)
        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info"] and not s.endswith(("C0", "CP0"))]
        tab1, tab2 = st.tabs(["📊 Analisi", "🖨️ Report"])

        with tab1:
            sel_sheet = st.selectbox("Seleziona Foglio", sheets)
            df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
            df_full.columns = [str(c).strip() for c in df_full.columns]
            found_cols = [c for c in df_full.columns if "CL_" in c and f"_{asse_sel}" in c]
            if found_cols:
                time_col = pd.to_datetime(df_full['Data e Ora'])
                df_cp0 = elaborazione_vba_originale(df_full[found_cols].ffill(), l_barra, sigma_val, limit_val)
                fig_hist = go.Figure()
                for i, col in enumerate(found_cols):
                    fig_hist.add_trace(go.Scatter(x=time_col, y=df_cp0.iloc[:, i], name=col))
                st.plotly_chart(fig_hist, use_container_width=True)

        with tab2:
            if st.button("🚀 GENERA REPORT WORD"):
                if not DOCX_AVAILABLE:
                    st.error("Errore librerie stampa.")
                else:
                    with st.spinner("Generazione..."):
                        doc = Document()
                        doc.add_heading('REPORT MONITORAGGIO', 0)
                        for l_name in sheets:
                            df_l = pd.read_excel(file_input, sheet_name=l_name)
                            cols_l = [c for c in df_l.columns if "CL_" in c and f"_{asse_sel}" in c]
                            if not cols_l: continue
                            df_res = elaborazione_vba_originale(df_l[cols_l].ffill(), l_barra, sigma_val, limit_val)
                            t_l = pd.to_datetime(df_l['Data e Ora'])
                            for idx, c_name in enumerate(cols_l):
                                serie_final = df_res.iloc[:, idx].rolling(5, center=True).mean().ffill().bfill()
                                plt.figure(figsize=(8, 3))
                                plt.plot(t_l, serie_final)
                                plt.title(f"Sensore {c_name}")
                                buf = BytesIO()
                                plt.savefig(buf, format='png')
                                plt.close()
                                doc.add_picture(buf, width=Inches(6))
                        target = BytesIO()
                        doc.save(target)
                        st.download_button("📥 Scarica", target.getvalue(), "Report.docx")
