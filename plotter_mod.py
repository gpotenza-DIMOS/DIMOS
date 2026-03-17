import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os
from io import BytesIO
from datetime import datetime

# --- GESTIONE LIBRERIA DOCX ---
try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- FUNZIONI DI CALCOLO E FILTRO ---
def applica_filtri_avanzati(serie, n_sigma, rimuovi_zeri):
    originale = serie.copy()
    diagnostica = {"zeri": 0, "gauss": 0}
    
    # 1. Rimozione Zeri
    if rimuovi_zeri:
        diagnostica["zeri"] = (originale == 0).sum()
        originale = originale.replace(0, np.nan)
    
    # 2. Filtro Gauss
    temp_data = originale.dropna()
    if not temp_data.empty and n_sigma > 0:
        mean = temp_data.mean()
        std = temp_data.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diagnostica["gauss"] = outliers.sum()
            originale[outliers] = np.nan
            
    return originale, diagnostica

@st.cache_resource
def get_data_from_excel(file_content):
    xls = pd.ExcelFile(file_content)
    df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
    data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
    df_values = pd.read_excel(xls, sheet_name=data_sheet)
    df_values.columns = [str(c).strip() for c in df_values.columns]
    col_tempo = next((c for c in df_values.columns if 'data' in str(c).lower()), None)
    if col_tempo:
        df_values[col_tempo] = pd.to_datetime(df_values[col_tempo], errors='coerce')
        df_values = df_values.dropna(subset=[col_tempo]).sort_values(by=col_tempo)
    return df_header, df_values, col_tempo

# --- GENERAZIONE REPORT WORD ---
def genera_report_word(fig, selezione, tipo_sel, sigma, zeri_on, d_range, stats):
    doc = Document()
    
    # Header e Titolo
    title = doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"Data estrazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n").bold = True
    p.add_run(f"Periodo: {d_range[0]} - {d_range[1]}\n")
    p.add_run(f"Grandezza: {tipo_sel}")

    # Grafico
    doc.add_heading('Analisi Grafica', level=1)
    img_bytes = fig.to_image(format="png", width=1000, height=500, scale=2)
    doc.add_picture(BytesIO(img_bytes), width=Inches(6))

    # Diagnostica Filtri
    doc.add_heading('Diagnostica e Qualità Dati', level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Sensore'
    hdr_cells[1].text = 'Zeri Rimossi'
    hdr_cells[2].text = 'Outliers (Gauss)'

    for s_name, s_stat in stats.items():
        row_cells = table.add_row().cells
        row_cells[0].text = s_name
        row_cells[1].text = str(s_stat['zeri'])
        row_cells[2].text = str(s_stat['gauss'])

    target = BytesIO()
    doc.save(target)
    return target.getvalue()

# --- INTERFACCIA PRINCIPALE ---
def run_plotter():
    st.header("📉 PLOTTER - Analisi e Reportistica")
    
    st.sidebar.header("⚙️ Filtri")
    rimuovi_zeri = st.sidebar.toggle("Elimina Zeri Puri", value=True)
    usa_filtro = st.sidebar.checkbox("Filtro Sigma Gauss", value=True)
    sigma_val = st.sidebar.slider("Sigma", 0.5, 5.0, 2.0, 0.1) if usa_filtro else 0
    
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plt_v_final")

    if not file_input:
        st.info("In attesa del file Excel...")
        return

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)

        # Mappatura
        sensor_map = []
        for col in range(1, len(df_header.columns)):
            id_t = str(df_header.iloc[2, col]).strip()
            lbl = f"{str(df_header.iloc[1, col]).strip()} ({str(df_header.iloc[0, col]).strip()})"
            if "[V]" in id_t.upper(): t = "Batteria (Volt)"
            elif "[°C]" in id_t.upper(): t = "Temperatura (°C)"
            elif "[°]" in id_t: t = "Inclinazione (°)"
            elif "[MM]" in id_t.upper(): t = "Spostamento (mm)"
            else: t = "Altro"
            sensor_map.append({'id': id_t, 'label': lbl, 'tipo': t})

        tipo_sel = st.selectbox("Grandezza Fisica:", sorted(list(set([s['tipo'] for s in sensor_map]))))
        opzioni = {s['label']: s['id'] for s in sensor_map if s['tipo'] == tipo_sel}
        selezione = st.multiselect("Seleziona Sensori:", list(opzioni.keys()))

        if selezione:
            min_d, max_d = df_values[col_tempo].min(), df_values[col_tempo].max()
            d_range = st.date_input("Periodo:", [min_d.date(), max_d.date()])
            
            if len(d_range) == 2:
                mask = (df_values[col_tempo].dt.date >= d_range[0]) & (df_values[col_tempo].dt.date <= d_range[1])
                df_plot = df_values.loc[mask].copy()

                fig = go.Figure()
                stats_final = {}

                for nome in selezione:
                    cid = opzioni[nome]
                    if cid in df_plot.columns:
                        y_raw = df_plot[cid]
                        y_clean, stats = applica_filtri_avanzati(y_raw, sigma_val, rimuovi_zeri)
                        stats_final[nome] = stats
                        
                        df_trace = pd.DataFrame({'x': df_plot[col_tempo], 'y': y_clean}).dropna()
                        fig.add_trace(go.Scatter(x=df_trace['x'], y=df_trace['y'], name=nome, 
                                                 mode='lines+markers', connectgaps=True))

                fig.update_layout(template="plotly_white", height=550, hovermode="x unified",
                                  xaxis=dict(rangeslider=dict(visible=True), tickformat="%d %b %y"))
                st.plotly_chart(fig, use_container_width=True)

                # Sezione Diagnostica a video
                with st.expander("🔍 Dettaglio Diagnostica Filtri"):
                    df_stats = pd.DataFrame(stats_final).T
                    df_stats.columns = ["Zeri Eliminati", "Outliers Gauss"]
                    st.table(df_stats)

                # Sezione Export Word
                st.divider()
                if st.button("📝 Genera Report Word (.docx)"):
                    if DOCX_AVAILABLE:
                        with st.spinner("Generazione report in corso..."):
                            doc_bytes = genera_report_word(fig, selezione, tipo_sel, sigma_val, rimuovi_zeri, d_range, stats_final)
                            st.download_button("📥 Scarica Report Word", doc_bytes, f"Report_{tipo_sel}.docx")
                    else:
                        st.error("Libreria 'python-docx' non installata.")

    except Exception as e:
        st.error(f"Errore: {e}")
