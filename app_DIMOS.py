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
    from docx.shared import Cm, Inches
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
    # Calcolo mm e delta C0 senza riempimenti artificiali
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    data_c0 = data_mm - data_mm[0, :]
    data_cp0 = np.cumsum(data_c0, axis=1)
    
    # Filtraggio outlier (mantenendo i NaN dove i dati mancano)
    data_cp0[np.abs(data_cp0) > limit_val] = np.nan
    means = np.nanmean(data_cp0, axis=0)
    stds = np.nanstd(data_cp0, axis=0)
    for j in range(data_cp0.shape[1]):
        m, s = means[j], stds[j]
        # Applica il filtro Sigma solo dove il dato esiste
        mask = (data_cp0[:, j] < m - n_sigma*s) | (data_cp0[:, j] > m + n_sigma*s)
        data_cp0[mask, j] = np.nan
        
    # Restituisce il DataFrame pulito senza forzare ffill() o fillna(0)
    return pd.DataFrame(data_cp0, index=df_values.index)

# --- ESECUZIONE PRINCIPALE ---
if check_password():
    p_main_logo = get_asset_path("logo_dimos.jpg")
    if os.path.exists(p_main_logo):
        st.image(p_main_logo, width=600)

    with st.sidebar:
        p_micro = get_asset_path("logo_microgeo.jpg")
        if os.path.exists(p_micro): st.image(p_micro, use_container_width=True)
        
        st.header("⚙️ Parametri")
        file_input = st.file_uploader("Carica Excel", type=['xls', 'xlsx', 'xlsm'])
        asse_sel = st.selectbox("Asse di Analisi", ["X", "Y", "Z"])
        
        st.divider()
        st.subheader("🎬 GRAFICO DINAMICO")
        step_video = st.select_slider(
            "Intervallo:",
            options=["Ogni Lettura", "1 Giorno", "2 Giorni", "3 Giorni", "1 Settimana"],
            value="1 Giorno"
        )
        vel_animazione = st.slider("Velocità Video (ms)", 100, 2000, 400)
        
        st.divider()
        st.subheader("🛡️ Parametri Fisici")
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
            
            sensor_order = []
            if "ARRAY" in xls.sheet_names:
                df_array = pd.read_excel(file_input, sheet_name="ARRAY", header=None)
                row_array = df_array[df_array[0] == sel_sheet]
                if not row_array.empty:
                    sensor_order = row_array.iloc[0, 1:].dropna().astype(float).astype(int).astype(str).tolist()
                    sensor_order = [s.zfill(3) for s in sensor_order]

            found_cols = [c for c in df_full.columns if "CL_" in c and f"_{asse_sel}" in c]
            
            if sensor_order:
                ordered_cols = []
                for s_id in sensor_order:
                    match = [c for c in found_cols if f"CL_{s_id}" in c]
                    if match: ordered_cols.append(match[0])
                sensor_cols = ordered_cols
            else:
                sensor_cols = found_cols

            if sensor_cols:
                time_col = pd.to_datetime(df_full['Data e Ora'])
                # Rimosso .ffill() dalla chiamata della funzione
                df_cp0 = elaborazione_vba_originale(df_full[sensor_cols], l_barra, sigma_val, limit_val)
                labels = [re.search(r'CL_(\d+)', c).group(1) for c in sensor_cols]

                st.subheader(f"🎬 Monitoraggio Deformata {asse_sel}: {sel_sheet}")
                df_calc = df_cp0.copy()
                df_calc['Data_Ora'] = time_col
                
                if step_video == "1 Giorno": df_sampled = df_calc.groupby(df_calc['Data_Ora'].dt.date).first()
                elif "Giorni" in step_video: 
                    days = int(step_video.split()[0])
                    df_sampled = df_calc.set_index('Data_Ora').resample(f'{days}D').first()
                elif "Settimana" in step_video: df_sampled = df_calc.set_index('Data_Ora').resample('W').first()
                else: df_sampled = df_calc.set_index('Data_Ora')
                
                df_sampled = df_sampled.drop(columns=['Data_Ora'], errors='ignore').dropna(how='all')

                fig_vid = go.Figure()
                fig_vid.add_trace(go.Scatter(
                    x=labels, y=df_sampled.iloc[0], 
                    mode='lines+markers+text',
                    text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_sampled.iloc[0]], 
                    textposition="top center"
                ))

                fig_vid.update_layout(
                    xaxis=dict(type='category', tickangle=-90, title="ID Sensore"),
                    yaxis=dict(range=[-limit_val-5, limit_val+5], title="mm"),
                    height=650, template="plotly_white",
                    sliders=[{"steps": [{"method": "animate", "label": str(t), 
                              "args": [[str(i)], {"frame": {"duration": vel_animazione, "redraw": True}}]} for i, t in enumerate(df_sampled.index)]}]
                )
                
                frames = [go.Frame(data=[go.Scatter(x=labels, y=df_sampled.iloc[i],
                          text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_sampled.iloc[i]],
                          marker=dict(size=12, color=['red' if pd.notnull(v) and abs(v)>=5 else 'orange' if pd.notnull(v) and abs(v)>=2 else 'green' if pd.notnull(v) else 'rgba(0,0,0,0)' for v in df_sampled.iloc[i]]))], name=str(i)) for i in range(len(df_sampled))]
                fig_vid.frames = frames
                st.plotly_chart(fig_vid, use_container_width=True)

                st.divider()
                st.subheader("📈 GRAFICO - Trend Temporale")
                sel_sens = st.multiselect("Seleziona sensori:", labels, default=labels[:3] if len(labels)>3 else labels)
                if sel_sens:
                    fig_hist = go.Figure()
                    for s in sel_sens:
                        idx_s = labels.index(s)
                        fig_hist.add_trace(go.Scatter(x=time_col, y=df_cp0.iloc[:, idx_s], name=f"CL_{s}", connectgaps=False))
                    fig_hist.update_layout(xaxis=dict(tickangle=-90), hovermode="x unified", template="plotly_white")
                    st.plotly_chart(fig_hist, use_container_width=True)
