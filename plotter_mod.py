import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
from datetime import datetime

# --- GESTIONE LIBRERIA DOCX (RIPRISTINATA) ---
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
    xls = pd.ExcelFile(file_content)
    # Legge i metadati dal foglio NAME (prime 3 righe)
    df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
    # Prende il secondo foglio per i dati
    data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
    df_values = pd.read_excel(xls, sheet_name=data_sheet)
    df_values.columns = [str(c).strip() for c in df_values.columns]
    
    col_tempo = next((c for c in df_values.columns if 'data' in str(c).lower() or 'time' in str(c).lower()), df_values.columns[0])
    df_values[col_tempo] = pd.to_datetime(df_values[col_tempo], errors='coerce')
    df_values = df_values.dropna(subset=[col_tempo]).sort_values(by=col_tempo)
    return df_header, df_values, col_tempo

# --- FUNZIONE REPORT WORD (RIPRISTINATA) ---
def genera_report_word(fig, stats, d_range, sigma, zeri_on):
    doc = Document()
    doc.add_heading('REPORT MONITORAGGIO TECNICO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    info = doc.add_paragraph()
    info.add_run(f"Data Report: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n").bold = True
    info.add_run(f"Periodo Analisi: {d_range[0]} - {d_range[1]}\n")
    info.add_run(f"Configurazione Filtri: Gauss ({sigma} σ), Rimozi. Zeri ({'Sì' if zeri_on else 'No'})")

    img_bytes = fig.to_image(format="png", width=1000, height=600, scale=2)
    doc.add_picture(BytesIO(img_bytes), width=Inches(6))

    doc.add_heading('Diagnostica Dati Rimossi', level=1)
    table = doc.add_table(rows=1, cols=3); table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = 'Canale', 'Zeri', 'Outliers'
    for s_name, s_diag in stats.items():
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = s_name, str(s_diag['zeri']), str(s_diag['gauss'])
    
    target = BytesIO()
    doc.save(target)
    return target.getvalue()

# --- INTERFACCIA ---
def run_plotter():
    st.header("📉 PLOTTER PRO - Multi-Parametro")
    
    with st.sidebar:
        st.header("⚙️ Configurazione")
        tipo_asse_x = st.radio("Asse X:", ["Temporale", "Sequenziale"])
        passo_date = st.number_input("Etichette ogni N date (Sequenziale):", value=400, min_value=1)
        st.divider()
        rimuovi_zeri = st.toggle("Rimuovi Zeri Puri", value=True)
        usa_gauss = st.checkbox("Attiva Filtro Gauss", value=True)
        sigma = st.slider("Sigma (Sensibilità)", 0.5, 5.0, 2.0) if usa_gauss else 0
        
    file_input = st.sidebar.file_uploader("Carica File Excel (con foglio NAME)", type=['xlsx', 'xlsm'])
    if not file_input: return st.info("In attesa del file Excel...")

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)
        
        # --- MAPPATURA AVANZATA ---
        mappa_tipi = {} # { "Inclinazione": { "Sensore A": { "Canale ID": "Suffisso" } } }
        for col in range(1, len(df_header.columns)):
            logger = str(df_header.iloc[0, col])
            nome_sensore = str(df_header.iloc[1, col])
            id_canale = str(df_header.iloc[2, col])
            
            if "[°]" in id_canale: t = "Inclinazione (°)"
            elif "°C" in id_canale: t = "Temperatura (°C)"
            elif "[m]" in id_canale: t = "Distanza (m)"
            elif "[V]" in id_canale: t = "Batteria (Volt)"
            else: t = "Altro/Diagnostica"

            if t not in mappa_tipi: mappa_tipi[t] = {}
            full_name = f"{nome_sensore} ({logger})"
            if full_name not in mappa_tipi[t]: mappa_tipi[t][full_name] = {}
            
            # Estrae l'ultima parte dell'ID (es. X, Y, T1, LI)
            suffix = id_canale.split()[-2] if len(id_canale.split()) > 2 else id_canale
            mappa_tipi[t][full_name][id_canale] = suffix

        # --- SELEZIONE UI ---
        tipi_scelti = st.multiselect("1. Seleziona Grandezze:", sorted(mappa_tipi.keys()))
        
        final_targets = {} # { "Inclinazione": { "Label": "ID_Colonna" } }
        if tipi_scelti:
            for t in tipi_scelti:
                st.write(f"#### Configurazione {t}")
                sensori_in_tipo = st.multiselect(f"Sensori per {t}:", list(mappa_tipi[t].keys()), key=f"s_{t}")
                if sensori_in_tipo:
                    final_targets[t] = {}
                    cols = st.columns(len(sensori_scelti) if len(sensori_in_tipo) > 0 else 1) # Layout dinamico
                    for idx, s in enumerate(sensori_in_tipo):
                        canali_disp = mappa_tipi[t][s]
                        scelti = st.multiselect(f"Assi per {s}:", list(canali_disp.keys()), 
                                               format_func=lambda x: canali_disp[x], key=f"c_{s}")
                        for c in scelti:
                            final_targets[t][f"{s} - {canali_disp[c]}"] = c

        if final_targets:
            st.divider()
            c1, c2 = st.columns(2)
            with c1: start_d = st.date_input("Inizio:", df_values[col_tempo].min().date())
            with c2: end_d = st.date_input("Fine:", df_values[col_tempo].max().date())
            
            df_p = df_values[(df_values[col_tempo].dt.date >= start_d) & 
                             (df_values[col_tempo].dt.date <= end_d)].copy().reset_index(drop=True)
            
            # --- GENERAZIONE SUBPLOTS ---
            n_rows = len(final_targets)
            fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                               subplot_titles=list(final_targets.keys()))
            
            stats_final = {}
            for row_idx, (tipo, canali_dict) in enumerate(final_targets.items(), 1):
                for label, cid in canali_dict.items():
                    y_clean, diag = applica_filtri_completi(df_p[cid], sigma, rimuovi_zeri)
                    stats_final[label] = diag
                    
                    temp_df = pd.DataFrame({'x_val': df_p.index if tipo_asse_x == "Sequenziale" else df_p[col_tempo], 
                                          'y_val': y_clean}).dropna()
                    
                    fig.add_trace(go.Scatter(x=temp_df['x_val'], y=temp_df['y_val'], name=label, 
                                             mode='lines+markers', connectgaps=True), row=row_idx, col=1)

            # --- FORMATTAZIONE ASSE X (DINAMICA E SEQUENZIALE) ---
            if tipo_asse_x == "Sequenziale":
                ticks = [row[col_tempo].strftime('%d/%m/%y %H:%M') if i % passo_date == 0 else "" for i, row in df_p.iterrows()]
                fig.update_xaxes(tickmode='array', tickvals=list(df_p.index), ticktext=ticks, tickangle=-45)
            
            fig.update_layout(template="plotly_white", height=400 * n_rows, hovermode="x unified",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # --- ESPORTAZIONE ---
            col_ex1, col_ex2 = st.columns([2, 1])
            with col_ex1:
                with st.expander("📊 Diagnostica Filtri"):
                    st.table(pd.DataFrame(stats_final).T)
            with col_ex2:
                if st.button("Genera Report Word"):
                    if DOCX_AVAILABLE:
                        doc_b = genera_report_word(fig, stats_final, [start_d, end_d], sigma, rimuovi_zeri)
                        st.download_button("📥 Scarica Report", doc_b, f"Report_Analisi.docx")
                    else:
                        st.error("Libreria docx non configurata.")

    except Exception as e:
        st.error(f"Errore tecnico: {e}")

if __name__ == "__main__":
    run_plotter()
