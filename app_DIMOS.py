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

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Monitoraggio Avanzato Elettrolivelle", layout="wide")

# --- GESTIONE LOGHI (RIPRISTINATI) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_asset_path(filename):
    return os.path.join(BASE_DIR, filename)

# --- SISTEMA DI AUTENTICAZIONE (RIPRISTINATO) ---
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

# --- MOTORE DI CALCOLO (AGGIORNATO CON LOGICA VBA RICHIESTA) ---
@st.cache_data(show_spinner=False)
def elaborazione_vba_originale(df_values, l_barra, n_sigma):
    # 1. BONIFICA ZERI
    df_values = df_values.replace(0, np.nan)
    
    # Conversione gradi -> mm
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    
    # 2. DELTA SINGOLO (Rispetto a prima riga, no cumulata)
    data_c0 = data_mm - data_mm[0, :]
    
    # Filtraggio Outlier Sigma Gauss
    data_processed = data_c0.copy()
    means = np.nanmean(data_processed, axis=0)
    stds = np.nanstd(data_processed, axis=0)
    
    for j in range(data_processed.shape[1]):
        m, s = means[j], stds[j]
        mask = (data_processed[:, j] < m - n_sigma*s) | (data_processed[:, j] > m + n_sigma*s)
        data_processed[mask, j] = m
        
    return pd.DataFrame(data_processed, index=df_values.index)

# --- FUNZIONE LOGICA COLORI ---
def get_marker_colors(values):
    colors = []
    for v in values:
        if pd.isnull(v): colors.append('rgba(0,0,0,0)')
        elif abs(v) >= 5: colors.append('red')
        elif abs(v) >= 2: colors.append('orange')
        else: colors.append('green')
    return colors

# --- FUNZIONE ESPORTAZIONE EXCEL (Richiesta 5: C, C0, CP0) ---
def export_to_excel_full(df_raw, l_barra, n_sigma):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_clean = df_raw.replace(0, np.nan)
        
        # Foglio C (mm)
        df_c = l_barra * np.sin(np.radians(df_clean.values))
        df_c_out = pd.DataFrame(df_c, index=df_raw.index, columns=df_raw.columns)
        df_c_out.to_excel(writer, sheet_name='C')
        
        # Foglio C0 (Delta Singolo)
        df_c0 = df_c_out - df_c_out.iloc[0, :]
        df_c0.to_excel(writer, sheet_name='C0')
        
        # Foglio CP0 (Processato con soglie VBA)
        df_cp0 = elaborazione_vba_originale(df_raw, l_barra, n_sigma)
        df_cp0.to_excel(writer, sheet_name='CP0')
        
    return output.getvalue()

# --- FUNZIONE REPORT WORD (Richiesta 3 e 4) ---
def crea_report_word(df_data, time_col, sensor_labels):
    doc = Document()
    doc.add_heading('Report Monitoraggio - Analisi Trend', 0)
    for i, label in enumerate(sensor_labels):
        y_raw = df_data.iloc[:, i]
        
        # 4. MEDIA MOBILE 5 PUNTI
        y_smooth = y_raw.rolling(window=5, center=True).mean() 
        
        plt.figure(figsize=(10, 4))
        plt.plot(time_col, y_smooth, label='Media Mobile (5pt)', color='blue')
        
        # 4. TRENDLINE POLINOMIALE 3° GRADO
        valid = ~np.isnan(y_raw)
        if valid.any():
            x_num = np.arange(len(y_raw))
            z = np.polyfit(x_num[valid], y_raw[valid], 3)
            p = np.poly1d(z)
            plt.plot(time_col, p(x_num), '--', color='red', label='Trend Polinomiale')
            
        # 3. TITOLO PULITO (Senza parti barrate) e DATE ITALIANE
        plt.title(f'Sensore: {label}') 
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        # Formattazione asse date italiana
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m/%Y'))
        
        img_stream = BytesIO()
        plt.savefig(img_stream, format='png', bbox_inches='tight')
        doc.add_picture(img_stream, width=Inches(6))
        plt.close()
    
    out_word = BytesIO()
    doc.save(out_word)
    return out_word.getvalue()

# --- ESECUZIONE PRINCIPALE ---
if check_password():
    # Logo principale dopo login
    p_main_logo = get_asset_path("logo_dimos.jpg")
    if os.path.exists(p_main_logo):
        st.image(p_main_logo, width=600)

    with st.sidebar:
        p_micro = get_asset_path("logo_microgeo.jpg")
        if os.path.exists(p_micro):
            st.image(p_micro, use_container_width=True)
            
        st.header("⚙️ Parametri")
        file_input = st.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])
        asse_sel = st.selectbox("Asse di Analisi", ["X", "Y", "Z"])
        l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
        sigma_val = st.slider("Sigma Gauss", 1.0, 4.0, 2.0)
        limit_val = st.number_input("Limite Grafico (mm)", value=30.0)
        vel_animazione = st.slider("Velocità Video (ms)", 100, 2000, 400)
        
        if st.button("Logout"):
            st.session_state["auth"] = False
            st.rerun()

    if file_input:
        xls = pd.ExcelFile(file_input)
        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info"] and not s.endswith(("C0", "C", "CP0"))]
        
        tab1, tab2 = st.tabs(["📊 Analisi Dinamica", "🖨️ Report Word / Export"])
        
        with tab1:
            sel_sheet = st.selectbox("Seleziona Layer", sheets)
            df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
            time_col = pd.to_datetime(df_full['Data e Ora'])
            
            sensor_cols = [c for c in df_full.columns if "CL_" in str(c) and f"_{asse_sel}" in str(c)]
            
            if sensor_cols:
                df_cp0 = elaborazione_vba_originale(df_full[sensor_cols], l_barra, sigma_val)
                labels = [re.search(r'CL_(\d+)', c).group(1) for c in sensor_cols]
                
                st.subheader(f"🎬 Animazione Deformata Asse {asse_sel}")
                
                fig_vid = go.Figure()
                fig_vid.add_trace(go.Scatter(
                    x=labels, y=df_cp0.iloc[0],
                    mode='lines+markers+text',
                    text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_cp0.iloc[0]],
                    textposition="top center",
                    marker=dict(size=12, color=get_marker_colors(df_cp0.iloc[0]))
                ))

                fig_vid.update_layout(
                    xaxis=dict(type='category', title="ID Sensore"),
                    yaxis=dict(range=[-limit_val, limit_val], title="Spostamento (mm)"),
                    height=600, template="plotly_white",
                    sliders=[{
                        "steps": [{"method": "animate", "label": t.strftime('%d/%m/%Y %H:%M'), 
                                   "args": [[str(i)], {"frame": {"duration": vel_animazione, "redraw": True}}]} 
                                  for i, t in enumerate(time_col)]
                    }]
                )

                fig_vid.frames = [go.Frame(
                    data=[go.Scatter(
                        x=labels, y=df_cp0.iloc[i],
                        text=[f"{v:.2f}" if pd.notnull(v) else "" for v in df_cp0.iloc[i]],
                        marker=dict(color=get_marker_colors(df_cp0.iloc[i]))
                    )],
                    name=str(i)
                ) for i in range(len(df_cp0))]
                
                st.plotly_chart(fig_vid, use_container_width=True)

        with tab2:
            st.subheader("Generazione Output Locali")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 Genera Report Word"):
                    word_data = crea_report_word(df_cp0, time_col, labels)
                    st.download_button("Scarica .docx", word_data, "Report_Monitoraggio.docx")
            with c2:
                if st.button("📊 Esporta Excel Completo (C, C0, CP0)"):
                    excel_out = export_to_excel_full(df_full[sensor_cols], l_barra, sigma_val)
                    st.download_button("Scarica .xlsx", excel_out, "Dati_Elaborati.xlsx")
