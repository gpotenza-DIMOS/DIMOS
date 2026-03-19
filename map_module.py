import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import os

# --- GESTIONE LIBRERIA DOCX ---
try:
    from docx import Document
    from docx.shared import Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- LOGICA FILTRI ---
def applica_filtri_completi(serie, n_sigma, rimuovi_zeri):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    if rimuovi_zeri:
        diag["zeri"] = (originale == 0).sum()
        originale = originale.replace(0, np.nan)
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        mean, std = validi.mean(), validi.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diag["gauss"] = outliers.sum()
            originale[outliers] = np.nan
    return originale, diag

@st.cache_resource
def get_data_from_excel(file_content):
    try:
        xls = pd.ExcelFile(file_content)
        # Carica il foglio NAME per la mappatura
        df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
        
        # Carica il primo foglio che non sia NAME
        data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
        df_values = pd.read_excel(xls, sheet_name=data_sheet)
        
        # Pulizia nomi colonne
        df_values.columns = [str(c).strip() for c in df_values.columns]
        
        # RICERCA FLESSIBILE COLONNA TEMPORALE (Risolve KeyError)
        col_tempo = None
        possibili_nomi = ['data', 'time', 'ora', 'date']
        for c in df_values.columns:
            if any(nome in c.lower() for nome in possibili_nomi):
                col_tempo = c
                break
        
        if col_tempo:
            df_values[col_tempo] = pd.to_datetime(df_values[col_tempo], errors='coerce')
            df_values = df_values.dropna(subset=[col_tempo]).sort_values(by=col_tempo)
            return df_header, df_values, col_tempo
        else:
            st.error("⚠️ Colonna temporale non trovata. Assicurati che nel file ci sia una colonna 'Data e Ora'.")
            return None, None, None
    except Exception as e:
        st.error(f"❌ Errore nel caricamento del file: {e}")
        return None, None, None

def genera_report_word(fig, stats, tipo_sel, d_range, sigma, zeri_on):
    doc = Document()
    logo_path = "logo_dimos.jpg"
    if os.path.exists(logo_path):
        try: doc.add_picture(logo_path, width=Inches(1.5))
        except: pass
    
    doc.add_heading('REPORT MONITORAGGIO TECNICO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    info = doc.add_paragraph()
    info.add_run(f"Data Report: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n").bold = True
    info.add_run(f"Periodo: {d_range[0]} - {d_range[1]}\n")
    info.add_run(f"Filtri: Gauss ({sigma} σ), Zeri ({'On' if zeri_on else 'Off'})")

    try:
        img_bytes = fig.to_image(format="png", width=1000, height=500, scale=2)
        doc.add_picture(BytesIO(img_bytes), width=Inches(6))
    except Exception as e:
        doc.add_paragraph(f"\n[Grafico non disponibile nel report: {e}]\n")

    doc.add_heading('Diagnostica Dati', level=1)
    table = doc.add_table(rows=1, cols=3); table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = 'Canale', 'Zeri Rimossi', 'Outliers Gauss'
    for s_name, s_diag in stats.items():
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = s_name, str(s_diag['zeri']), str(s_diag['gauss'])
    
    target = BytesIO()
    doc.save(target)
    return target.getvalue()

def run_plotter():
    st.header("📉 PLOTTER PRO")
    
    with st.sidebar:
        st.header("⚙️ Impostazioni")
        tipo_asse_x = st.radio("Asse X:", ["Sequenziale (Stile Excel)", "Temporale"])
        passo_date = st.number_input("Etichette ogni N date:", value=400, min_value=1)
        st.divider()
        rimuovi_zeri = st.toggle("Rimuovi Zeri Puri", value=True)
        usa_gauss = st.checkbox("Attiva Gauss", value=True)
        sigma = st.slider("Sigma", 0.5, 5.0, 2.0) if usa_gauss else 0
        
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])
    
    if file_input:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)
        
        if df_values is not None and col_tempo is not None:
            # Mappatura Struttura
            mappa = {}
            for col in range(1, len(df_header.columns)):
                id_t = str(df_header.iloc[2, col])
                nome = str(df_header.iloc[1, col])
                logger = str(df_header.iloc[0, col])
                
                # Riconoscimento tipo
                if "[°]" in id_t: t = "Inclinazione (°)"
                elif "°C" in id_t.upper(): t = "Temperatura (°C)"
                elif "MM" in id_t.upper(): t = "Spostamento (mm)"
                elif "[V]" in id_t.upper(): t = "Batteria (V)"
                else: t = "Altro"
                
                key = f"{nome} ({logger})"
                if key not in mappa: mappa[key] = {"tipo": t, "canali": {}}
                
                # Prendi l'ultima parte dell'ID per l'asse (X, Y, Z...)
                suffix = id_t.split()[-2] if len(id_t.split()) > 2 else id_t
                mappa[key]["canali"][id_t] = suffix

            tipo_sel = st.selectbox("Grandezza:", sorted(list(set([v['tipo'] for v in mappa.values()]))))
            sensori_disp = [k for k, v in mappa.items() if v['tipo'] == tipo_sel]
            sensori_scelti = st.multiselect("Sensori:", sensori_disp)

            final_targets = {}
            if sensori_scelti:
                st.write("### 🎯 Selezione Assi")
                cols = st.columns(len(sensori_scelti))
                for i, s in enumerate(sensori_scelti):
                    with cols[i]:
                        canali = mappa[s]["canali"]
                        scelte = st.multiselect(f"{s}:", list(canali.keys()), format_func=lambda x: canali[x])
                        for sc in scelte:
                            final_targets[f"{s} - {canali[sc]}"] = sc

            if final_targets:
                st.divider()
                c1, c2 = st.columns(2)
                with c1: start_d = st.date_input("Inizio:", df_values[col_tempo].min().date())
                with c2: end_d = st.date_input("Fine:", df_values[col_tempo].max().date())
                
                if start_d <= end_d:
                    df_p = df_values[(df_values[col_tempo].dt.date >= start_d) & (df_values[col_tempo].dt.date <= end_d)].copy().reset_index(drop=True)
                    
                    fig = go.Figure()
                    stats_final = {}
                    
                    for label, cid in final_targets.items():
                        if cid in df_p.columns:
                            y_clean, diag = applica_filtri_completi(df_p[cid], sigma, rimuovi_zeri)
                            stats_final[label] = diag
                            
                            temp_df = pd.DataFrame({'idx': df_p.index, 'time': df_p[col_tempo], 'y': y_clean}).dropna(subset=['y'])
                            x_axis = temp_df['idx'] if "Sequenziale" in tipo_asse_x else temp_df['time']
                            
                            fig.add_trace(go.Scatter(x=x_axis, y=temp_df['y'], name=label, mode='lines+markers', connectgaps=True))

                    # Formattazione Asse X
                    if "Sequenziale" in tipo_asse_x:
                        ticks = [row[col_tempo].strftime('%d/%m/%y %H:%M') if i % passo_date == 0 else "" for i, row in df_p.iterrows()]
                        fig.update_layout(xaxis=dict(type='category', tickmode='array', tickvals=list(df_p.index), ticktext=ticks, tickangle=-45))
                    
                    fig.update_layout(template="plotly_white", height=600, hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Diagnostica e Word
                    cd1, cd2 = st.columns([2, 1])
                    with cd1:
                        with st.expander("📊 Diagnostica"):
                            st.table(pd.DataFrame(stats_final).T)
                    with cd2:
                        if st.button("📝 Report Word"):
                            if DOCX_AVAILABLE:
                                doc_b = genera_report_word(fig, stats_final, tipo_sel, [start_d, end_d], sigma, rimuovi_zeri)
                                st.download_button("📥 Scarica", doc_b, f"Report_{tipo_sel}.docx")
    else:
        st.info("👋 Carica un file Excel per iniziare.")
