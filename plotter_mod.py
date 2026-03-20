import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# --- LIBRERIE STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    import plotly.io as pio
    DOC_OK = True
except:
    DOC_OK = False

def run_plotter():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=250)
    
    st.header("📈 Sistema Plotter DIMOS - Full Granularity")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'])
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
    
    # Carichiamo il primo foglio dati disponibile per mappare le colonne reali
    sheets = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    # --- 1. MAPPATURA GRANULARE (FIX SD_301) ---
    anagrafica = {}
    for c_idx in range(1, df_name.shape[1]):
        dl = str(df_name.iloc[0, c_idx]).strip()
        sens = str(df_name.iloc[1, c_idx]).strip()
        web_root = str(df_name.iloc[2, c_idx]).strip()
        
        if dl == "nan" or web_root == "nan": continue
        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        
        # Cerchiamo nel foglio dati TUTTE le colonne che contengono la radice web (es. CO_9277 CL_01)
        for col_real in df.columns:
            if web_root in col_real:
                # Puliamo l'etichetta per mostrare solo la grandezza (es. X [°])
                label = col_real.replace(web_root, "").strip().lstrip('_')
                if not label and "[" in col_real:
                    label = re.search(r'\[.*?\]', col_real).group(0)
                if not label: label = col_real # fallback
                
                anagrafica[dl][sens][label] = col_real

    # --- 2. SIDEBAR E FILTRI ---
    st.sidebar.header("🛠️ Analisi & Trend")
    do_zeros = st.sidebar.checkbox("Rimuovi Zeri", value=True)
    do_gauss = st.sidebar.checkbox("Filtro Gaussiano", value=True)
    sigma = st.sidebar.slider("Sigma (Outliers)", 1.0, 5.0, 2.0)
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 3. SELEZIONE ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Periodo", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: s_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    
    opts_s = [f"{d} | {s}" for d in s_dls for s in anagrafica[d].keys()]
    with c2: s_sens = st.multiselect("Sensore", opts_s)
    
    opts_g = set()
    for item in s_sens:
        d, s = item.split(" | ")
        opts_g.update(anagrafica[d][s].keys())
    with c3: s_grands = st.multiselect("Grandezza Fisica", sorted(list(opts_g)))

    # --- 4. CALCOLO E GRAFICO ---
    report_list = []
    fig = go.Figure()

    if s_sens and s_grands:
        for item in s_sens:
            d, s = item.split(" | ")
            for g in s_grands:
                if g in anagrafica[d][s]:
                    c_name = anagrafica[d][s][g]
                    y_raw = df_f[c_name].copy()
                    
                    # Diagnostica
                    z_count = (y_raw == 0).sum()
                    if do_zeros: y_raw = y_raw.replace(0, np.nan)
                    
                    g_count = 0
                    if do_gauss and y_raw.notna().sum() > 5:
                        m, sd = y_raw.mean(), y_raw.std()
                        outliers = abs(y_raw - m) > (sigma * sd)
                        g_count = outliers.sum()
                        y_raw = y_raw.mask(outliers, np.nan)
                    
                    y_clean = y_raw.interpolate(limit_direction='both')
                    report_list.append({"ID": f"{s}-{g}", "Zeri": z_count, "Gauss": g_count})

                    # Dati
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_clean, name=f"{s} - {g}"))
                    
                    # Trend
                    if grado_poly > 0:
                        x_ax = np.arange(len(y_clean))
                        mask = y_clean.notna()
                        if mask.any():
                            p = np.poly1d(np.polyfit(x_ax[mask], y_clean[mask], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_ax), 
                                                   name=f"Trend {s}-{g}", line=dict(dash='dot')))

        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame(report_list))

        # --- 5. STAMPA SPECULARE ---
        st.divider()
        if st.button("🚀 PRODUCI REPORT WORD"):
            doc = Document()
            doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
            img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
            doc.add_picture(img_io, width=Inches(6.2))
            
            # Tabella diagnostica nel report
            table = doc.add_table(rows=1, cols=3); table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = 'Sensore/Grandezza'; hdr[1].text = 'Zeri Rimos.'; hdr[2].text = 'Outlier Gauss'
            for r in report_list:
                row = table.add_row().cells
                row[0].text = r['ID']; row[1].text = str(r['Zeri']); row[2].text = str(r['Gauss'])
            
            buf = BytesIO(); doc.save(buf)
            st.download_button("📥 Scarica Report Word", buf.getvalue(), "Report.docx")
