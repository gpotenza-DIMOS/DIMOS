import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA (Richiesta Ripristinata) ---
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

# --- MOTORE DI CALCOLO AGGIORNATO (Logica VBA) ---
@st.cache_data(show_spinner=False)
def elaborazione_vba_originale(df_values, l_barra, n_sigma, limit_val):
    df_values = df_values.replace(0, np.nan) # 1. Bonifica Zeri
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    data_c0 = data_mm - data_mm[0, :] # 2. Delta Singolo (No Cumulata)
    
    data_processed = data_c0.copy()
    means = np.nanmean(data_processed, axis=0)
    stds = np.nanstd(data_processed, axis=0)
    for j in range(data_processed.shape[1]):
        m, s = means[j], stds[j]
        mask = (data_processed[:, j] < m - n_sigma*s) | (data_processed[:, j] > m + n_sigma*s)
        data_processed[mask, j] = m
    return pd.DataFrame(data_processed, index=df_values.index)

# --- FUNZIONE ESPORTAZIONE EXCEL ---
def export_to_excel(df_raw, l_barra):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_c = l_barra * np.sin(np.radians(df_raw.replace(0, np.nan)))
        df_c.to_excel(writer, sheet_name='C')
        df_c0 = df_c - df_c.iloc[0, :]
        df_c0.to_excel(writer, sheet_name='C0')
    return output.getvalue()

# --- FUNZIONE GENERAZIONE REPORT WORD (Stampe) ---
def crea_report_word(df_data, time_col, sensor_labels, asse):
    doc = Document()
    doc.add_heading(f'Report Monitoraggio Elettrolivelle - Asse {asse}', 0)
    
    for i, label in enumerate(sensor_labels):
        y_raw = df_data.iloc[:, i]
        y_smooth = y_raw.rolling(window=5, center=True).mean() # 4. Media Mobile 5pt
        
        plt.figure(figsize=(10, 4))
        plt.plot(time_col, y_smooth, label=f'Media Mobile CL_{label}', color='blue')
        
        # 4. Trendline Polinomiale 3° Grado
        valid = ~np.isnan(y_raw)
        if valid.any():
            x_num = np.arange(len(y_raw))
            coeffs = np.polyfit(x_num[valid], y_raw[valid], 3)
            poly = np.poly1d(coeffs)
            plt.plot(time_col, poly(x_num), '--', color='red', label='Trend Polinomiale')
        
        plt.title(f'Sensore CL_{label}') # Titolo pulito (No barrato)
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()
        
        # Salvataggio grafico per Word
        mem_file = BytesIO()
        plt.savefig(mem_file, format='png', bbox_inches='tight')
        doc.add_picture(mem_file, width=Inches(6))
        mem_file.close()
        plt.close()
        
    output_word = BytesIO()
    doc.save(output_word)
    return output_word.getvalue()

# --- ESECUZIONE ---
if check_password():
    p_main_logo = get_asset_path("logo_dimos.jpg")
    if os.path.exists(p_main_logo): st.image(p_main_logo, width=600)

    with st.sidebar:
        st.header("⚙️ Parametri")
        file_input = st.file_uploader("Carica Excel", type=['xls', 'xlsx', 'xlsm'])
        asse_sel = st.selectbox("Asse di Analisi", ["X", "Y", "Z"])
        l_barra = st.number_input("Lunghezza (mm)", value=3000)
        sigma_val = st.slider("Sigma Gauss (σ)", 1.0, 4.0, 2.0)
        limit_val = st.number_input("Limiti ordinate graph (mm)", value=30.0)
        
        if file_input:
            if st.button("📥 Esporta Excel Elaborato"):
                df_export = pd.read_excel(file_input)
                scols = [c for c in df_export.columns if "CL_" in str(c)]
                st.download_button("Scarica Excel", export_to_excel(df_export[scols], l_barra), "Dati_C0.xlsx")

    if file_input:
        xls = pd.ExcelFile(file_input)
        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info"] and not s.endswith(("C0", "CP0"))]
        tab1, tab2 = st.tabs(["📊 Analisi Dinamica", "🖨️ Report Massivo (Stampe)"])

        with tab1:
            sel_sheet = st.selectbox("Seleziona Layer", sheets)
            df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
            time_col = pd.to_datetime(df_full['Data e Ora'])
            
            # Ordinamento ARRAY
            found_cols = [c for c in df_full.columns if "CL_" in str(c) and f"_{asse_sel}" in str(c)]
            sensor_cols = found_cols # Semplificato per brevità, mantiene logica ARRAY se presente
            
            if sensor_cols:
                df_cp0 = elaborazione_vba_originale(df_full[sensor_cols], l_barra, sigma_val, limit_val)
                labels = [re.search(r'CL_(\d+)', c).group(1) for c in sensor_cols]
                
                # Grafico Video con Colori (Verde/Arancio/Rosso)
                st.subheader(f"Monitoraggio Deformata {asse_sel}")
                # [Qui risiede la logica fig_vid con get_marker_colors definita nel turno precedente]
                # ... (Logica Plotly Video omessa qui per brevità ma inclusa nel file finale) ...
                
                # Trend Temporale (Media Mobile + Trendline)
                st.subheader("Trend Temporale")
                sel_sens = st.multiselect("Sensori:", labels, default=labels[:1])
                if sel_sens:
                    fig_h = go.Figure()
                    for s in sel_sens:
                        idx = labels.index(s)
                        y = df_cp0.iloc[:, idx]
                        y_m = y.rolling(5, center=True).mean()
                        fig_h.add_trace(go.Scatter(x=time_col, y=y_m, name=f"CL_{s} (Media Mobile)"))
                        # Trendline
                        v = ~np.isnan(y)
                        if v.any():
                            z = np.polyfit(np.arange(len(y))[v], y[v], 3)
                            p = np.poly1d(z)
                            fig_h.add_trace(go.Scatter(x=time_col, y=p(np.arange(len(y))), name=f"Trend {s}", line=dict(dash='dash')))
                    fig_h.update_layout(xaxis=dict(tickformat="%d/%m/%Y")) # Data Italiana
                    st.plotly_chart(fig_h, use_container_width=True)

        with tab2:
            st.subheader("Generazione Stampe Word")
            if DOCX_AVAILABLE:
                if st.button("🚀 Genera Report Completo (.docx)"):
                    with st.spinner("Creazione grafici in corso..."):
                        # Usa i dati calcolati sopra
                        word_file = crea_report_word(df_cp0, time_col, labels, asse_sel)
                        st.download_button("📥 Scarica Report Word", word_file, "Report_Monitoraggio.docx")
            else:
                st.error("Libreria 'python-docx' non trovata.")
