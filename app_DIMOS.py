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
    return pd.DataFrame(data_cp0, index=df_values.index).ffill().fillna(0)

# --- ESECUZIONE PRINCIPALE ---
if check_password():
    p_main_logo = get_asset_path("logo_dimos.jpg")
    if os.path.exists(p_main_logo):
        st.image(p_main_logo, width=600)

    with st.sidebar:
        p_micro = get_asset_path("logo_microgeo.jpg") # Corretto in .jpg come file caricati
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
                df_cp0 = elaborazione_vba_originale(df_full[sensor_cols].ffill(), l_barra, sigma_val, limit_val)
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
                    text=[f"{v:.2f}" for v in df_sampled.iloc[0]], 
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
                          text=[f"{v:.2f}" for v in df_sampled.iloc[i]],
                          marker=dict(size=12, color=['red' if abs(v)>=5 else 'orange' if abs(v)>=2 else 'green' for v in df_sampled.iloc[i]]))], name=str(i)) for i in range(len(df_sampled))]
                fig_vid.frames = frames
                st.plotly_chart(fig_vid, use_container_width=True)

                st.divider()
                st.subheader("📈 GRAFICO - Trend Temporale")
                sel_sens = st.multiselect("Seleziona sensori:", labels, default=labels[:3] if len(labels)>3 else labels)
                if sel_sens:
                    fig_hist = go.Figure()
                    for s in sel_sens:
                        idx_s = labels.index(s)
                        fig_hist.add_trace(go.Scatter(x=time_col, y=df_cp0.iloc[:, idx_s], name=f"CL_{s}"))
                    fig_hist.update_layout(xaxis=dict(tickangle=-90), hovermode="x unified", template="plotly_white")
                    st.plotly_chart(fig_hist, use_container_width=True)

        with tab2:
            st.subheader("🖨️ Centro Stampa Massiva")
            layers_print = st.multiselect("Layer da esportare:", sheets, default=sheets)
            
            if st.button("🚀 GENERA DOCUMENTAZIONE WORD"):
                if not DOCX_AVAILABLE:
                    st.error("Librerie Word non pronte.")
                else:
                    with st.spinner("Generazione Report in corso..."):
                        doc = Document()
                        doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                        
                        for l_name in layers_print:
                            doc.add_page_break()
                            doc.add_heading(f'LAYER: {l_name}', level=1)
                            
                            df_l = pd.read_excel(file_input, sheet_name=l_name)
                            df_l.columns = [str(c).strip() for c in df_l.columns]
                            cols_l = [c for c in df_l.columns if "CL_" in c and f"_{asse_sel}" in c]
                            
                            if not cols_l: continue
                            
                            df_res = elaborazione_vba_originale(df_l[cols_l].ffill(), l_barra, sigma_val, limit_val)
                            t_l = pd.to_datetime(df_l['Data e Ora'])
                            
                            for idx, c_name in enumerate(cols_l):
                                s_id = re.search(r'CL_(\d+)', c_name).group(1)
                                
                                # LOGICA VBA: PULIZIA SIGMA 2 E MEDIA MOBILE 5 PUNTI
                                serie = df_res.iloc[:, idx]
                                m_val, d_val = serie.mean(), serie.std()
                                serie_p = serie.mask(abs(serie - m_val) > (2 * d_val), m_val)
                                serie_final = serie_p.rolling(5, center=True).mean().ffill().bfill()
                                
                                # GRAFICO MATPLOTLIB (Sostituisce Plotly per la stampa)
                                plt.figure(figsize=(10, 4))
                                plt.plot(t_l, serie_final, color='blue', linewidth=1)
                                plt.title(f"Sensore {s_id} - Layer {l_name}")
                                plt.grid(True, linestyle='--', alpha=0.7)
                                plt.ylabel("mm")
                                
                                buf = BytesIO()
                                plt.savefig(buf, format='png', bbox_inches='tight')
                                plt.close()
                                buf.seek(0)
                                
                                doc.add_paragraph(f"Trend Temporale Sensore: {s_id}")
                                doc.add_picture(buf, width=Inches(6))
                        
                        target_file = BytesIO()
                        doc.save(target_file)
                        st.download_button(label="📥 Scarica Report Word", data=target_file.getvalue(), file_name=f"Report_DIMOS_{asse_sel}.docx")
    else:
        st.info("Benvenuto sul portale DIMOS. Carica un file Excel per iniziare.")