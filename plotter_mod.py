import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from io import BytesIO
from datetime import datetime

# --- GESTIONE LIBRERIA DOCX ---
try:
    from docx import Document
    from docx.shared import Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- LOGICA FILTRI ---
def applica_filtri_avanzati(serie, n_sigma, rimuovi_zeri):
    originale = serie.copy()
    diagnostica = {"zeri": 0, "gauss": 0}
    if rimuovi_zeri:
        diagnostica["zeri"] = (originale == 0).sum()
        originale = originale.replace(0, np.nan)
    temp_data = originale.dropna()
    if not temp_data.empty and n_sigma > 0:
        mean, std = temp_data.mean(), temp_data.std()
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

# --- GENERAZIONE REPORT ---
def genera_report_word(fig, selezione_finale, tipo_sel, sigma, zeri_on, d_range, stats):
    doc = Document()
    doc.add_heading('REPORT MONITORAGGIO DIMOS - PLOTTER', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    doc.add_paragraph(f"Grandezza: {tipo_sel} | Periodo: {d_range[0]} - {d_range[1]}")
    
    img_bytes = fig.to_image(format="png", width=1000, height=500, scale=2)
    doc.add_picture(BytesIO(img_bytes), width=Inches(6))

    doc.add_heading('Diagnostica Dati', level=1)
    table = doc.add_table(rows=1, cols=3); table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = 'Canale/Asse', 'Zeri Rimossi', 'Outliers Gauss'
    for s_name, s_stat in stats.items():
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = s_name, str(s_stat['zeri']), str(s_stat['gauss'])
    
    target = BytesIO()
    doc.save(target)
    return target.getvalue()

def run_plotter():
    st.header("📉 PLOTTER - Multi-Asse e Diagnostica")
    
    st.sidebar.header("⚙️ Configurazione")
    rimuovi_zeri = st.sidebar.toggle("Elimina Zeri Puri", value=True)
    usa_filtro = st.sidebar.checkbox("Filtro Sigma Gauss", value=True)
    sigma_val = st.sidebar.slider("Sigma", 0.5, 5.0, 2.0, 0.1) if usa_filtro else 0
    
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plt_v_axes")
    if not file_input: return st.info("Carica un file Excel per iniziare.")

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)
        
        # 1. MAPPATURA AVANZATA (Raggruppamento per Sensore Umano)
        mappa_sensori = {}
        for col in range(1, len(df_header.columns)):
            datalogger = str(df_header.iloc[0, col]).strip()
            nome_umano = str(df_header.iloc[1, col]).strip()
            id_tech = str(df_header.iloc[2, col]).strip()
            
            # Identificazione Tipo
            if "[V]" in id_tech.upper(): t = "Batteria (Volt)"
            elif "[°C]" in id_tech.upper(): t = "Temperatura (°C)"
            elif "[°]" in id_tech: t = "Inclinazione (°)"
            elif "[MM]" in id_tech.upper(): t = "Spostamento (mm)"
            else: t = "Altro"
            
            label_gruppo = f"{nome_umano} ({datalogger})"
            if label_gruppo not in mappa_sensori:
                mappa_sensori[label_gruppo] = {"tipo": t, "canali": {}}
            
            # Estraiamo l'asse o il suffisso (es: _X, _Y, _Z o VAR1)
            suffix = id_tech.split()[-2] if len(id_tech.split()) > 2 else id_tech
            mappa_sensori[label_gruppo]["canali"][id_tech] = suffix

        # 2. SELEZIONE INTERFACCIA
        tipo_sel = st.selectbox("Seleziona Grandezza Fisica:", sorted(list(set([s['tipo'] for s in mappa_sensori.values()]))))
        
        sensori_per_tipo = [name for name, d in mappa_sensori.items() if d['tipo'] == tipo_sel]
        sensori_scelti = st.multiselect("Seleziona Sensori:", sensori_per_tipo)

        selezione_finale = {}
        if sensori_scelti:
            st.divider()
            st.subheader("🎯 Selezione Assi / Canali")
            cols = st.columns(len(sensori_scelti))
            for i, s_name in enumerate(sensori_scelti):
                with cols[i % len(cols)]:
                    canali_disp = mappa_sensori[s_name]["canali"]
                    scelte_assi = st.multiselect(f"Assi per {s_name}:", list(canali_disp.keys()), 
                                                 default=list(canali_disp.keys())[:1],
                                                 format_func=lambda x: canali_disp[x])
                    for a in scelte_assi:
                        selezione_finale[f"{s_name} - {canali_disp[a]}"] = a

        if selezione_finale:
            min_d, max_d = df_values[col_tempo].min(), df_values[col_tempo].max()
            d_range = st.date_input("Periodo:", [min_d.date(), max_d.date()])
            
            if len(d_range) == 2:
                mask = (df_values[col_tempo].dt.date >= d_range[0]) & (df_values[col_tempo].dt.date <= d_range[1])
                df_plot = df_values.loc[mask].copy()
                fig = go.Figure()
                stats_final = {}

                for label_grafico, cid in selezione_finale.items():
                    if cid in df_plot.columns:
                        y_clean, stats = applica_filtri_avanzati(df_plot[cid], sigma_val, rimuovi_zeri)
                        stats_final[label_grafico] = stats
                        df_trace = pd.DataFrame({'x': df_plot[col_tempo], 'y': y_clean}).dropna()
                        fig.add_trace(go.Scatter(x=df_trace['x'], y=df_trace['y'], name=label_grafico, 
                                                 mode='lines+markers', connectgaps=True))

                fig.update_layout(template="plotly_white", height=600, hovermode="x unified",
                                  xaxis=dict(rangeslider=dict(visible=True), tickformat="%d %b %y"))
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("🔍 Diagnostica Canali Selezionati"):
                    st.table(pd.DataFrame(stats_final).T.rename(columns={"zeri": "Zeri Rimossi", "gauss": "Outliers Gauss"}))

                if st.button("📝 Genera Report Word"):
                    if DOCX_AVAILABLE:
                        doc_b = genera_report_word(fig, selezione_finale, tipo_sel, sigma_val, rimuovi_zeri, d_range, stats_final)
                        st.download_button("📥 Scarica Word", doc_b, f"Report_{tipo_sel}.docx")

    except Exception as e:
        st.error(f"Errore: {e}")
