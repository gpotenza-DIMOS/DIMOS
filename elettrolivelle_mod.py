import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    import plotly.io as pio
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- MOTORE DI CALCOLO (Identico al tuo VBA) ---
@st.cache_data(show_spinner=False)
def calcolo_motore_vba(df_values, l_barra, n_sigma, limit_val):
    # Conversione Angolo -> mm: L * sin(rad(deg))
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    # Delta C0: Valore attuale - Prima lettura
    data_c0 = data_mm - data_mm[0, :]
    # Deformata Cumulata CP0 (Somma orizzontale)
    data_cp0 = np.cumsum(data_c0, axis=1)
    
    # Filtro Limiti Hard
    data_cp0[np.abs(data_cp0) > limit_val] = np.nan
    
    # Filtro Sigma Gauss su ogni sensore
    means = np.nanmean(data_cp0, axis=0)
    stds = np.nanstd(data_cp0, axis=0)
    for j in range(data_cp0.shape[1]):
        m, s = means[j], stds[j]
        if s > 0:
            mask = (data_cp0[:, j] < m - n_sigma*s) | (data_cp0[:, j] > m + n_sigma*s) | (np.isnan(data_cp0[:, j]))
            data_cp0[mask, j] = m
            
    return pd.DataFrame(data_cp0, index=df_values.index).ffill().fillna(0)

# --- FUNZIONE PRINCIPALE (Richiamata da app_DIMOS.py) ---
def run_elettrolivelle():
    st.header("📏 Monitoraggio Avanzato Elettrolivelle")

    # Sidebar: Parametri Tecnici
    with st.sidebar:
        st.divider()
        st.subheader("⚙️ Parametri Analisi")
        file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsm', 'xlsx'], key="el_up")
        
        if file_input:
            asse_sel = st.selectbox("Asse di Analisi", ["X", "Y", "Z"], key="el_asse")
            l_barra = st.number_input("Lunghezza Barre/Distanza (mm)", value=3000)
            sigma_val = st.slider("Filtro Sigma Gauss (σ)", 1.0, 4.0, 2.0)
            limit_val = st.number_input("Limiti Ordinate Graph (mm)", value=30.0)
            
            st.divider()
            st.subheader("🎬 Opzioni Video")
            step_video = st.select_slider(
                "Intervallo Campionamento:",
                options=["Ogni Lettura", "1 Giorno", "2 Giorni", "3 Giorni", "1 Settimana"],
                value="1 Giorno"
            )
            vel_animazione = st.slider("Velocità Video (ms)", 100, 2000, 400)

    if not file_input:
        st.info("Benvenuto. Carica un file Excel per attivare l'analisi delle deformate.")
        return

    # Lettura Excel
    xls = pd.ExcelFile(file_input)
    # Filtro fogli: solo quelli che iniziano con ETS_ e non sono fogli di calcolo pregressi
    sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info"] and not s.endswith(("C0", "CP0"))]
    
    tab1, tab2 = st.tabs(["📊 Analisi Dinamica", "🖨️ Report Word Massivo"])

    with tab1:
        sel_sheet = st.selectbox("Seleziona Layer/Stringa", sheets)
        df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
        df_full.columns = [str(c).strip() for c in df_full.columns]
        time_col = pd.to_datetime(df_full['Data e Ora'])

        # --- LOGICA ARRAY: ORDINAMENTO FISICO ---
        sensor_order = []
        if "ARRAY" in xls.sheet_names:
            df_array = pd.read_excel(file_input, sheet_name="ARRAY", header=None)
            row_array = df_array[df_array[0] == sel_sheet]
            if not row_array.empty:
                # Prende gli ID sensore, li formatta CL_XXX
                sensor_order = row_array.iloc[0, 1:].dropna().astype(float).astype(int).astype(str).tolist()
                sensor_order = [s.zfill(3) for s in sensor_order]

        # Selezione colonne sensori basata sull'ordine ARRAY
        found_cols = [c for c in df_full.columns if "CL_" in c and f"_{asse_sel}" in c]
        if sensor_order:
            sensor_cols = []
            for s_id in sensor_order:
                match = [c for c in found_cols if f"CL_{s_id}" in c]
                if match: sensor_cols.append(match[0])
        else:
            sensor_cols = found_cols

        if not sensor_cols:
            st.warning(f"Nessun sensore trovato per l'asse {asse_sel} nel foglio {sel_sheet}")
            return

        # Calcolo Deformata
        df_cp0 = calcolo_motore_vba(df_full[sensor_cols].ffill(), l_barra, sigma_val, limit_val)
        labels = [re.search(r'CL_(\d+)', c).group(1) for c in sensor_cols]

        # Campionamento Temporale per Video
        df_calc = df_cp0.copy()
        df_calc['Data_Ora'] = time_col
        if step_video == "1 Giorno":
            df_sampled = df_calc.groupby(df_calc['Data_Ora'].dt.date).first()
        elif "Giorni" in step_video:
            days = int(step_video.split()[0])
            df_sampled = df_calc.set_index('Data_Ora').resample(f'{days}D').first()
        elif "Settimana" in step_video:
            df_sampled = df_calc.set_index('Data_Ora').resample('W').first()
        else:
            df_sampled = df_calc.set_index('Data_Ora')
        
        df_sampled = df_sampled.drop(columns=['Data_Ora'], errors='ignore').dropna(how='all')

        # --- GRAFICO DINAMICO (VIDEO) ---
        st.subheader(f"🎬 Deformata {asse_sel}: {sel_sheet}")
        fig_vid = go.Figure()
        fig_vid.add_trace(go.Scatter(
            x=labels, y=df_sampled.iloc[0], 
            mode='lines+markers+text',
            text=[f"{v:.2f}" for v in df_sampled.iloc[0]], 
            textposition="top center",
            line=dict(color="#1f77b4", width=2)
        ))

        fig_vid.update_layout(
            xaxis=dict(type='category', title="ID Sensore (Ordine Fisico)"),
            yaxis=dict(range=[-limit_val-2, limit_val+2], title="Cumulata (mm)"),
            height=600, template="plotly_white",
            sliders=[{"active": 0, "steps": [{"method": "animate", "label": str(t), 
                      "args": [[str(i)], {"frame": {"duration": vel_animazione, "redraw": True}}]} 
                      for i, t in enumerate(df_sampled.index)]}]
        )
        
        fig_vid.frames = [go.Frame(data=[go.Scatter(
            x=labels, y=df_sampled.iloc[i],
            text=[f"{v:.2f}" for v in df_sampled.iloc[i]],
            marker=dict(size=12, color=['red' if abs(v)>=5 else 'orange' if abs(v)>=2 else 'green' for v in df_sampled.iloc[i]])
        )], name=str(i)) for i in range(len(df_sampled))]
        
        st.plotly_chart(fig_vid, use_container_width=True)

        # --- TREND TEMPORALE ---
        st.divider()
        st.subheader("📈 Analisi Trend Temporale")
        sel_sens = st.multiselect("Seleziona sensori da confrontare:", labels, default=labels[:3] if len(labels)>3 else labels)
        if sel_sens:
            fig_hist = go.Figure()
            for s in sel_sens:
                idx = labels.index(s)
                fig_hist.add_trace(go.Scatter(x=time_col, y=df_cp0.iloc[:, idx], name=f"CL_{s}"))
            fig_hist.update_layout(xaxis=dict(title="Tempo"), yaxis=dict(title="mm"), hovermode="x unified", template="plotly_white")
            st.plotly_chart(fig_hist, use_container_width=True)

    with tab2:
        st.subheader("🖨️ Generazione Report Word Massivo")
        layers_print = st.multiselect("Seleziona Layer da includere nel report:", sheets, default=sheets)
        
        if st.button("🚀 GENERA DOCUMENTO WORD COMPLETO"):
            if not DOCX_AVAILABLE:
                st.error("Libreria 'python-docx' non installata.")
            else:
                with st.spinner("Calcolo e generazione grafici in corso..."):
                    doc = Document()
                    doc.add_heading('REPORT MONITORAGGIO DIMOS - ELETTROLIVELLE', 0)
                    
                    for l_name in layers_print:
                        doc.add_page_break()
                        doc.add_heading(f'LAYER: {l_name} - ASSE {asse_sel}', level=1)
                        
                        df_l = pd.read_excel(file_input, sheet_name=l_name)
                        cols_l = [c for c in df_l.columns if "CL_" in c and f"_{asse_sel}" in c]
                        df_res = calcolo_motore_vba(df_l[cols_l].ffill(), l_barra, sigma_val, limit_val)
                        t_l = pd.to_datetime(df_l['Data e Ora'])
                        
                        for idx, c_name in enumerate(cols_l):
                            s_id = re.search(r'CL_(\d+)', c_name).group(1)
                            
                            # Logica VBA: Pulizia Sigma 2 e Media Mobile 5 punti (come da tuo OTTIMO)
                            serie = df_res.iloc[:, idx]
                            m_val, d_val = serie.mean(), serie.std()
                            serie_p = serie.mask(abs(serie - m_val) > (2 * d_val), m_val)
                            serie_final = serie_p.rolling(5, center=True).mean().ffill().bfill()
                            
                            fig_tmp = go.Figure()
                            fig_tmp.add_trace(go.Scatter(x=t_l, y=serie_final, line=dict(color='blue', width=1.5)))
                            fig_tmp.update_layout(title=f"Sensore CL_{s_id} - Trend Temporale", width=900, height=400)
                            
                            img_stream = BytesIO(pio.to_image(fig_tmp, format="png"))
                            doc.add_paragraph(f"Andamento temporale sensore: {s_id}")
                            doc.add_picture(img_stream, width=Inches(6.2))

                    target_file = BytesIO()
                    doc.save(target_file)
                    st.download_button(label="📥 Scarica Report Word", data=target_file.getvalue(), file_name=f"Report_DIMOS_{asse_sel}.docx")
