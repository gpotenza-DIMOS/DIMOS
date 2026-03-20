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
    # Logo
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=250)
    
    st.header("📈 Plotter DIMOS - Analisi Avanzata & Diagnostica")

    file_input = st.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
    
    # Mappatura Esplosa (X, Y, Z, T1, LM...)
    anagrafica = {}
    for c_idx in range(1, df_name.shape[1]):
        dl = str(df_name.iloc[0, c_idx]).strip()
        sens = str(df_name.iloc[1, c_idx]).strip()
        web_id = str(df_name.iloc[2, c_idx]).strip()
        if dl == "nan" or web_id == "nan": continue
        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        
        # Cerchiamo tutte le varianti nel foglio dati
        df_cols = pd.read_excel(xls, sheet_name=xls.sheet_names[0], nrows=0).columns
        for c in df_cols:
            if web_id in str(c):
                g_label = str(c).replace(web_id, "").strip().lstrip('_')
                if not g_label and "[" in str(c):
                    g_label = re.search(r'\[.*?\]', str(c)).group(0)
                anagrafica[dl][sens][g_label] = str(c)

    # Sidebar: Filtri con Report
    st.sidebar.header("🛠️ Impostazioni Filtri")
    do_zeros = st.sidebar.checkbox("Rimuovi Zeri (0.00)", value=True)
    do_gauss = st.sidebar.checkbox("Filtro Outlier (Gauss)", value=True)
    sigma = st.sidebar.slider("Sigma (Sensibilità)", 1.0, 5.0, 2.0)
    grado_poly = st.sidebar.selectbox("Grado Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # Caricamento Dati
    sheets = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    df = pd.read_excel(xls, sheet_name=sheets[0])
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])
    
    # Selezione Temporale
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Intervallo", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    # Selezione Granulare
    c1, c2, c3 = st.columns(3)
    with c1: sel_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    opts_s = [f"{d} | {s}" for d in sel_dls for s in anagrafica[d].keys()]
    with c2: sel_sens = st.multiselect("Sensore", opts_s)
    opts_g = set()
    for item in sel_sens:
        d, s = item.split(" | ")
        opts_g.update(anagrafica[d][s].keys())
    with c3: sel_grands = st.multiselect("Grandezza Fisica", sorted(list(opts_g)))

    # ELABORAZIONE CON REPORT
    report_data = []
    fig = go.Figure()

    if sel_sens and sel_grands:
        for item in sel_sens:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]:
                    col = anagrafica[d][s][g]
                    y_raw = df_f[col].copy()
                    
                    # 1. Conteggio Zeri
                    zeros_found = (y_raw == 0).sum()
                    if do_zeros: y_raw = y_raw.replace(0, np.nan)
                    
                    # 2. Conteggio Gauss
                    gauss_removed = 0
                    if do_gauss and y_raw.notna().sum() > 5:
                        m, sd = y_raw.mean(), y_raw.std()
                        outliers = abs(y_raw - m) > (sigma * sd)
                        gauss_removed = outliers.sum()
                        y_raw = y_raw.mask(outliers, np.nan)
                    
                    y_clean = y_raw.interpolate(limit_direction='both')
                    
                    # Report per questo sensore
                    report_data.append({
                        "Sensore": s, "Grandezza": g, 
                        "Zeri rimossi": zeros_found, 
                        "Outlier Gauss": gauss_removed,
                        "Punti Totali": len(y_clean)
                    })

                    # Grafico Dati e Trend
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_clean, name=f"{s} - {g}"))
                    
                    if grado_poly > 0:
                        x_idx = np.arange(len(y_clean))
                        mask = y_clean.notna()
                        if mask.any():
                            p = np.poly1d(np.polyfit(x_idx[mask], y_clean[mask], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_idx), 
                                                   name=f"Trend {s} ({g})", line=dict(dash='dot')))

        st.plotly_chart(fig, use_container_width=True)
        
        # VISUALIZZAZIONE REPORT A VIDEO
        st.subheader("📊 Diagnostica Pulizia Dati")
        st.table(pd.DataFrame(report_data))

        # STAMPE SPECULARI
        st.divider()
        if st.button("🚀 AVVIA PRODUZIONE REPORT WORD"):
            doc = Document()
            doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
            
            # Immagine speculare
            img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
            doc.add_picture(img_io, width=Inches(6.2))
            
            # Tabella diagnostica nel Word
            doc.add_heading('Diagnostica e Qualità Dati', level=2)
            table = doc.add_table(rows=1, cols=4); table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = 'Sensore/Grandezza'; hdr[1].text = 'Zeri Rimossi'; hdr[2].text = 'Outlier Gauss'; hdr[3].text = 'Punti Tot'
            
            for r in report_data:
                row = table.add_row().cells
                row[0].text = f"{r['Sensore']} - {r['Grandezza']}"
                row[1].text = str(r['Zeri rimossi'])
                row[2].text = str(r['Outlier Gauss'])
                row[3].text = str(r['Punti Totali'])
            
            out = BytesIO(); doc.save(out)
            st.download_button("📥 Scarica Word", out.getvalue(), "Report_Diagnostico.docx")

if __name__ == "__main__":
    run_plotter()
