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
    from docx.shared import Cm, Inches
    import plotly.io as pio
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- MOTORE DI CALCOLO (Logica VBA Originale) ---
@st.cache_data(show_spinner=False)
def elaborazione_vba_originale(df_values, l_barra, n_sigma, limit_val):
    # Calcolo mm: L * sin(rad(deg))
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    # Delta rispetto alla prima lettura (C0)
    data_c0 = data_mm - data_mm[0, :]
    # Deformata Cumulata (CP0)
    data_cp0 = np.cumsum(data_c0, axis=1)
    
    # Filtro Limiti
    data_cp0[np.abs(data_cp0) > limit_val] = np.nan
    
    # Filtro Sigma Gauss
    means = np.nanmean(data_cp0, axis=0)
    stds = np.nanstd(data_cp0, axis=0)
    for j in range(data_cp0.shape[1]):
        m, s = means[j], stds[j]
        mask = (data_cp0[:, j] < m - n_sigma*s) | (data_cp0[:, j] > m + n_sigma*s) | (np.isnan(data_cp0[:, j]))
        data_cp0[mask, j] = m
        
    return pd.DataFrame(data_cp0, index=df_values.index).ffill().fillna(0)

def run_elettrolivelle_advanced():
    """Funzione principale richiamata da app_DIMOS.py"""
    
    st.header("📏 Monitoraggio Avanzato Deformate")

    # --- SIDEBAR PARAMETRI ---
    with st.sidebar:
        st.divider()
        st.subheader("⚙️ Parametri di Calcolo")
        file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xls', 'xlsx', 'xlsm'], key="up_adv")
        asse_sel = st.selectbox("Asse di Analisi", ["X", "Y", "Z"], key="asse_adv")
        
        st.divider()
        st.subheader("🎬 Configurazione Animazione")
        step_video = st.select_slider(
            "Campionamento Temporale:",
            options=["Ogni Lettura", "1 Giorno", "2 Giorni", "3 Giorni", "1 Settimana"],
            value="1 Giorno"
        )
        vel_animazione = st.slider("Velocità (ms)", 100, 2000, 400)
        
        st.divider()
        l_barra = st.number_input("Lunghezza Barre (mm)", value=3000)
        sigma_val = st.slider("Filtro Sigma (Gauss)", 1.0, 4.0, 2.0)
        limit_val = st.number_input("Soglia Errore (mm)", value=30.0)

    if file_input:
        xls = pd.ExcelFile(file_input)
        # Escludiamo fogli di servizio
        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "Info", "NAME"] and not s.endswith(("C0", "CP0"))]
        
        tab1, tab2 = st.tabs(["📊 Analisi Dinamica", "🖨️ Report Massivo"])

        with tab1:
            sel_sheet = st.selectbox("Seleziona Stringa/Layer", sheets)
            df_full = pd.read_excel(file_input, sheet_name=sel_sheet)
            df_full.columns = [str(c).strip() for c in df_full.columns]
            
            # --- LOGICA ORDINAMENTO DA FOGLIO ARRAY ---
            sensor_order = []
            if "ARRAY" in xls.sheet_names:
                df_array = pd.read_excel(file_input, sheet_name="ARRAY", header=None)
                row_array = df_array[df_array[0] == sel_sheet]
                if not row_array.empty:
                    # Estrae i numeri, li converte in stringhe zfilled (es. 001)
                    sensor_order = row_array.iloc[0, 1:].dropna().astype(float).astype(int).astype(str).tolist()
                    sensor_order = [s.zfill(3) for s in sensor_order]

            # Identificazione colonne dati
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
                # Gestione colonna tempo
                col_tempo = df_full.columns[0] # Assume la prima colonna sia il tempo
                time_col = pd.to_datetime(df_full[col_tempo])
                
                df_cp0 = elaborazione_vba_originale(df_full[sensor_cols].ffill(), l_barra, sigma_val, limit_val)
                labels = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in sensor_cols]

                st.subheader(f"🎬 Video Deformata {asse_sel}: {sel_sheet}")
                
                # Sincronizzazione per campionamento
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

                # --- PLOTLY ANIMATION ---
                fig_vid = go.Figure()
                fig_vid.add_trace(go.Scatter(
                    x=labels, y=df_sampled.iloc[0], 
                    mode='lines+markers+text',
                    text=[f"{v:.2f}" for v in df_sampled.iloc[0]], 
                    textposition="top center",
                    line=dict(color="blue", width=2),
                    marker=dict(size=10, color="blue")
                ))

                fig_vid.update_layout(
                    xaxis=dict(type='category', title="ID Sensore (Sequenza Fisica)"),
                    yaxis=dict(range=[-limit_val-2, limit_val+2], title="Deformata Cumulata (mm)"),
                    height=600, template="plotly_white",
                    sliders=[{
                        "active": 0,
                        "currentvalue": {"prefix": "Data: "},
                        "steps": [{"method": "animate", "label": str(t), 
                                   "args": [[str(i)], {"frame": {"duration": vel_animazione, "redraw": True}}]} 
                                  for i, t in enumerate(df_sampled.index)]
                    }]
                )
                
                # Creazione frames per l'animazione
                frames = []
                for i in range(len(df_sampled)):
                    vals = df_sampled.iloc[i]
                    # Colore dinamico basato sulle soglie
                    colors = ['red' if abs(v) >= 10 else 'orange' if abs(v) >= 5 else 'green' for v in vals]
                    frames.append(go.Frame(data=[go.Scatter(
                        x=labels, y=vals,
                        text=[f"{v:.2f}" for v in vals],
                        marker=dict(size=12, color=colors)
                    )], name=str(i)))
                
                fig_vid.frames = frames
                st.plotly_chart(fig_vid, use_container_width=True)

                # --- TREND STORICO ---
                st.divider()
                st.subheader("📈 Trend Temporale Sensori")
                sel_sens = st.multiselect("Seleziona sensori da confrontare:", labels, default=labels[:2])
                if sel_sens:
                    fig_hist = go.Figure()
                    for s in sel_sens:
                        # Trova l'indice originale per recuperare i dati corretti
                        try:
                            idx = labels.index(s)
                            fig_hist.add_trace(go.Scatter(x=time_col, y=df_cp0.iloc[:, idx], name=f"Sensore {s}"))
                        except: pass
                    fig_hist.update_layout(template="plotly_white", hovermode="x unified")
                    st.plotly_chart(fig_hist, use_container_width=True)

        with tab2:
            st.subheader("🖨️ Esportazione Report Massivo")
            layers_print = st.multiselect("Layer da includere nel Word:", sheets, default=sheets)
            
            if st.button("🚀 GENERA DOCUMENTAZIONE WORD"):
                if not DOCX_AVAILABLE:
                    st.error("Librerie python-docx o plotly-io non configurate sul server.")
                else:
                    with st.spinner("Generazione in corso... potrebbe richiedere un minuto."):
                        doc = Document()
                        doc.add_heading('DIMOS - REPORT TECNICO ELETTROLIVELLE', 0)
                        
                        for l_name in layers_print:
                            doc.add_page_break()
                            doc.add_heading(f'Layer: {l_name}', level=1)
                            
                            # Ricalcolo veloce per il report
                            df_l = pd.read_excel(file_input, sheet_name=l_name)
                            cols_l = [c for c in df_l.columns if "CL_" in c and f"_{asse_sel}" in c]
                            df_res = elaborazione_vba_originale(df_l[cols_l].ffill(), l_barra, sigma_val, limit_val)
                            t_l = pd.to_datetime(df_l.iloc[:, 0])
                            
                            for idx, c_name in enumerate(cols_l):
                                s_id = re.search(r'CL_(\d+)', c_name).group(1) if "CL_" in c_name else c_name
                                
                                # Applichiamo piccola media mobile per pulizia estetica report
                                serie_f = df_res.iloc[:, idx].rolling(5, center=True).mean().ffill().bfill()
                                
                                # Grafico statico
                                fig_tmp = go.Figure()
                                fig_tmp.add_trace(go.Scatter(x=t_l, y=serie_f, line=dict(color='blue', width=1)))
                                fig_tmp.update_layout(title=f"Trend Sensore {s_id}", width=700, height=300)
                                
                                try:
                                    img_bytes = pio.to_image(fig_tmp, format="png")
                                    img_stream = BytesIO(img_bytes)
                                    doc.add_paragraph(f"Analisi Sensore: {s_id}")
                                    doc.add_picture(img_stream, width=Inches(6))
                                except Exception as e:
                                    st.error(f"Errore generazione immagine per {s_id}: {e}")

                        target_file = BytesIO()
                        doc.save(target_file)
                        st.download_button(label="📥 Scarica Report Word", data=target_file.getvalue(), file_name=f"Report_DIMOS_{asse_sel}.docx")

    else:
        st.info("Carica un file Excel per attivare l'analisi dinamica.")

# Se eseguito da solo (per test)
if __name__ == "__main__":
    run_elettrolivelle_advanced()
