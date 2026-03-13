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
st.set_page_config(page_title="DIMOS - Monitoraggio Avanzato Elettrolivelle", layout="wide")

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
        
        st.markdown("<h2 style='text-align: center;'>Accesso al Sistema</h2>", unsafe_allow_html=True)
        user_id = st.text_input("ID Utente")
        password = st.text_input("Password", type="password")
        
        if st.button("Entra"):
            if user_id == "dimos" and password == "micai!":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("ID o Password errati.")
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
        st.image(p_main_logo, width=600)

    with st.sidebar:
        p_micro = get_asset_path("logo_microgeo.jpg") 
        if os.path.exists(p_micro): 
            st.image(p_micro, use_container_width=True)
        
        st.header("⚙️ Parametri")
        file_input = st.file_uploader("Carica Excel", type=['xls', 'xlsx', 'xlsm'])
        asse_sel = st.selectbox("Asse di Analisi", ["X", "Y", "Z"])
        
        l_barra = st.number_input("Lunghezza (mm)", value=3000)
        sigma_val = st.slider("Sigma Gauss (σ)", 1.0, 4.0, 2.0)
        limit_val = st.number_input("Limiti ordinate graph (mm)", value=30.0)
        
        if st.button("Logout"):
            st.session_state["auth"] = False
            st.rerun()

    if file_input:
        xls = pd.ExcelFile(file_input)
        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info"] and not s.endswith(("C0", "CP0"))]
        tab1, tab2 = st.tabs(["📊 Analisi Dinamica", "🖨️ Report Massivo"])

        with tab1:
            sel_sheet = st.selectbox("Seleziona Layer", sheets)
            df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
            df_full.columns = [str(c).strip() for c in df_full.columns]
            
            found_cols = [c for c in df_full.columns if "CL_" in c and f"_{asse_sel}" in c]
            if found_cols:
                time_col = pd.to_datetime(df_full['Data e Ora'])
                df_cp0 = elaborazione_vba_originale(df_full[found_cols].ffill(), l_barra, sigma_val, limit_val)
                labels = [re.search(r'CL_(\d+)', c).group(1) for c in found_cols]
                
                fig_hist = go.Figure()
                for i, s in enumerate(labels):
                    fig_hist.add_trace(go.Scatter(x=time_col, y=df_cp0.iloc[:, i], name=f"CL_{s}"))
                st.plotly_chart(fig_hist, use_container_width=True)

        with tab2:
            st.subheader("🖨️ Centro Stampa Report")
            if st.button("🚀 GENERA DOCUMENTAZIONE WORD"):
                if not DOCX_AVAILABLE:
                    st.error("Libreria python-docx non installata.")
                else:
                    with st.spinner("Generazione Report..."):
                        doc = Document()
                        doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                        for l_name in sheets:
                            doc.add_heading(f'Layer: {l_name}', level=1)
                            df_l = pd.read_excel(file_input, sheet_name=l_name)
                            df_l.columns = [str(c).strip() for c in df_l.columns]
                            cols_l = [c for c in df_l.columns if "CL_" in c and f"_{asse_sel}" in c]
                            if not cols_l: continue
                            
                            df_res = elaborazione_vba_originale(df_l[cols_l].ffill(), l_barra, sigma_val, limit_val)
                            t_l = pd.to_datetime(df_l['Data e Ora'])
                            
                            for idx, c_name in enumerate(cols_l):
                                s_id = re.search(r'CL_(\d+)', c_name).group(1)
                                serie_final = df_res.iloc[:, idx].rolling(5, center=True).mean().ffill().bfill()
                                
                                # GRAFICO MATPLOTLIB (Senza dipendenze esterne come Kaleido)
                                plt.figure(figsize=(10, 4))
                                plt.plot(t_l, serie_final)
                                plt.title(f"Sensore {s_id}")
                                plt.grid(True)
                                
                                img_stream = BytesIO()
                                plt.savefig(img_stream, format='png')
                                plt.close()
                                img_stream.seek(0)
                                
                                doc.add_paragraph(f"Trend Temporale Sensore: {s_id}")
                                doc.add_picture(img_stream, width=Inches(6))
                        
                        target_file = BytesIO()
                        doc.save(target_file)
                        st.download_button("📥 Scarica Report", target_file.getvalue(), f"Report_{asse_sel}.docx")
