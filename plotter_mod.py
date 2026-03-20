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
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def run_plotter():
    # --- LOGO E TITOLO ---
    col_logo, _ = st.columns([1, 2])
    with col_logo:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", width=300)
    st.header("📈 Analisi Comparativa Multisensore")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="plot_up")
    if not file_input:
        st.info("Carica un file Excel per attivare i filtri di selezione.")
        return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. MAPPATURA GERARCHICA (NAME o WEB) ---
    anagrafica = {}
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None) if "NAME" in xls.sheet_names else None

    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    
    time_col = pd.to_datetime(df['Data e Ora'])

    # Popolamento Anagrafica
    cols_data = [c for c in df.columns if '[' in c]
    for col in cols_data:
        dl, sens, grandezza = None, None, None
        if df_name is not None:
            for c_idx in range(1, df_name.shape[1]):
                web_r3 = str(df_name.iloc[2, c_idx]).strip()
                if web_r3 in col:
                    dl = str(df_name.iloc[0, c_idx]).strip()
                    sens = str(df_name.iloc[1, c_idx]).strip()
                    grandezza = col.split(web_r3)[-1].strip()
                    if not grandezza: grandezza = re.search(r'\[.*?\]', col).group(0)
                    break
        if not dl: # Fallback
            parts = col.split(' ')
            dl = parts[0]
            unita = re.search(r'\[.*?\]', col).group(0) if '[' in col else ""
            sens_web = col.replace(dl, "").replace(unita, "").strip()
            sens = sens_web.split('_')[0] if '_' in sens_web else sens_web
            grandezza = sens_web.replace(sens, "").strip() + " " + unita

        grandezza = grandezza.lstrip('_').strip()
        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        anagrafica[dl][sens][grandezza] = col

    # --- 2. FILTRO TEMPORALE ---
    st.divider()
    t_min, t_max = time_col.min().to_pydatetime(), time_col.max().to_pydatetime()
    sel_range = st.slider("Intervallo Temporale", t_min, t_max, (t_min, t_max))
    df_plot = df[(time_col >= sel_range[0]) & (time_col <= sel_range[1])].copy()

    # --- 3. SELEZIONE MULTIPLA A CASCATA ---
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_dls = st.multiselect("1. Seleziona Datalogger", sorted(anagrafica.keys()))
    
    # Costruisco la lista sensori basata sui DL scelti
    opzioni_sensori = []
    if sel_dls:
        for d in sel_dls:
            for s in anagrafica[d].keys():
                opzioni_sensori.append(f"{d} | {s}")
    
    with c2:
        sel_sens_full = st.multiselect("2. Seleziona Sensori", opzioni_sensori)
    
    # Costruisco la lista grandezze basata sui sensori scelti
    opzioni_grandi = set()
    if sel_sens_full:
        for item in sel_sens_full:
            d, s = item.split(" | ")
            opzioni_grandi.update(anagrafica[d][s].keys())
    
    with c3:
        sel_grands = st.multiselect("3. Seleziona Grandezze Fisiche", sorted(list(opzioni_grandi)))

    # Opzione Trend
    grado_poly = st.sidebar.selectbox("Grado Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 4. GRAFICO ---
    if sel_sens_full and sel_grands:
        fig = go.Figure()
        
        for item in sel_sens_full:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]: # Verifico che il sensore abbia quella grandezza
                    col_raw = anagrafica[d][s][g]
                    y_vals = df_plot[col_raw].interpolate()
                    
                    # Traccia Dati
                    fig.add_trace(go.Scatter(x=df_plot['Data e Ora'], y=y_vals, name=f"{s} ({d}) - {g}"))
                    
                    # Trend
                    if grado_poly > 0:
                        x_num = np.arange(len(y_vals))
                        mask = ~y_vals.isna()
                        if mask.any():
                            z = np.polyfit(x_num[mask], y_vals[mask], grado_poly)
                            p = np.poly1d(z)
                            fig.add_trace(go.Scatter(x=df_plot['Data e Ora'], y=p(x_num), 
                                                   name=f"Trend {s} - {g}", line=dict(dash='dot', width=1)))

        fig.update_layout(template="plotly_white", hovermode="x unified", height=700,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # --- 5. REPORT WORD (STESSO CONTENUTO DEL GRAFICO) ---
        if st.button("🚀 GENERA REPORT WORD"):
            if DOCX_AVAILABLE:
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO MULTIPLO - DIMOS', 0)
                doc.add_paragraph(f"Periodo: {sel_range[0].strftime('%d/%m/%Y')} - {sel_range[1].strftime('%d/%m/%Y')}")
                
                # Info sui sensori inclusi
                doc.add_heading('Sensori e Grandezze incluse nel grafico:', level=2)
                for item in sel_sens_full:
                    doc.add_paragraph(f"• {item}", style='List Bullet')
                
                # Inserimento Grafico
                img_io = BytesIO(pio.to_image(fig, format="png", width=1200, height=600))
                doc.add_picture(img_io, width=Inches(6.4))
                
                target = BytesIO()
                doc.save(target)
                st.download_button("📥 Scarica Report Comparativo", target.getvalue(), "Report_Comparativo.docx")
