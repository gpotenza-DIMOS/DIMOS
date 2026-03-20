import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os
from io import BytesIO

try:
    from docx import Document
    from docx.shared import Inches
    import plotly.io as pio
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def run_plotter():
    # --- LOGO DIMOS ---
    col_l, _ = st.columns([1, 2])
    with col_l:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", width=300)
    
    st.header("📈 Sistema Plotter Multi-Selezione")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input:
        st.info("Carica il file per attivare i filtri multipli.")
        return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. MAPPATURA GERARCHICA RIGIDA ---
    # Struttura: { "DL_1": { "Sens_A": { "X [°]": "Colonna_Excel", ... } } }
    anagrafica = {}
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None) if "NAME" in xls.sheet_names else None

    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    
    time_col = pd.to_datetime(df['Data e Ora'])

    # Analisi colonne e creazione dizionario annidato
    cols_data = [c for c in df.columns if '[' in c]
    for col in cols_data:
        dl, sens, grandezza = None, None, None
        
        if df_name is not None:
            # Ricerca nel foglio NAME (Riga 3 = Nome Web)
            for c_idx in range(1, df_name.shape[1]):
                web_val = str(df_name.iloc[2, c_idx]).strip()
                if web_val in col:
                    dl = str(df_name.iloc[0, c_idx]).strip()
                    sens = str(df_name.iloc[1, c_idx]).strip()
                    # Isolo la grandezza fisica (es. X [°])
                    grandezza = col.split(web_val)[-1].lstrip('_').strip()
                    if not grandezza: 
                        grandezza = re.search(r'\[.*?\]', col).group(0)
                    break
        
        # Fallback se NAME non c'è o non trova match
        if not dl:
            parts = col.split(' ')
            dl = parts[0]
            unita = re.search(r'\[.*?\]', col).group(0) if '[' in col else ""
            sens_full = col.replace(dl, "").replace(unita, "").strip()
            # Gestione multisensore (CL_01_X)
            if '_' in sens_full:
                sens = "_".join(sens_full.split('_')[:-1])
                grandezza = sens_full.split('_')[-1] + " " + unita
            else:
                sens = sens_full
                grandezza = unita

        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        anagrafica[dl][sens][grandezza] = col

    # --- 2. SLIDER TEMPORALE ---
    st.divider()
    t_min, t_max = time_col.min().to_pydatetime(), time_col.max().to_pydatetime()
    sel_range = st.slider("Seleziona Periodo", t_min, t_max, (t_min, t_max))
    df_f = df[(time_col >= sel_range[0]) & (time_col <= sel_range[1])].copy()

    # --- 3. FILTRI MULTI-OPZIONE ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        # Puoi selezionare PIU' Datalogger
        sel_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    
    # Genero lista sensori per i DL scelti
    list_sens_opt = []
    for d in sel_dls:
        for s in anagrafica[d].keys():
            list_sens_opt.append(f"{d} | {s}")
    
    with c2:
        # Puoi selezionare PIU' Sensori di quei Datalogger
        sel_sens_full = st.multiselect("Sensori", list_sens_opt)
    
    # Genero lista grandezze per i sensori scelti
    list_grand_opt = set()
    for item in sel_sens_full:
        d, s = item.split(" | ")
        list_grand_opt.update(anagrafica[d][s].keys())
    
    with c3:
        # Puoi selezionare PIU' Grandezze (es. X e Y insieme)
        sel_grands = st.multiselect("Grandezze Fisiche", sorted(list(list_grand_opt)))

    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], 
                                     format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 4. GRAFICO ---
    if sel_sens_full and sel_grands:
        fig = go.Figure()
        
        for item in sel_sens_full:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]:
                    col_target = anagrafica[d][s][g]
                    y_data = df_f[col_target].interpolate()
                    
                    # Linea Dati
                    fig.add_trace(go.Scatter(x=df_f['Data Ora'], y=y_data, name=f"{s} ({d}) - {g}"))
                    
                    # Trend
                    if grado_poly > 0:
                        x_n = np.arange(len(y_data))
                        valid = ~y_data.isna()
                        if valid.any():
                            p = np.poly1d(np.polyfit(x_n[valid], y_data[valid], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data Ora'], y=p(x_n), 
                                                   name=f"Trend {s} {g}", line=dict(dash='dot', width=1)))

        fig.update_layout(template="plotly_white", hovermode="x unified", height=700,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # --- 5. STAMPA WORD COMPLETA ---
        if st.button("🚀 GENERA DOCUMENTO WORD"):
            if DOCX_AVAILABLE:
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                doc.add_paragraph(f"Intervallo: {sel_range[0]} - {sel_range[1]}")
                
                # Inserisco il grafico esattamente come configurato
                img_stream = BytesIO(pio.to_image(fig, format="png", width=1100, height=550))
                doc.add_picture(img_stream, width=Inches(6.4))
                
                # Tabella riassuntiva dei sensori inclusi
                doc.add_heading('Elenco Sensori Selezionati', level=2)
                for s_item in sel_sens_full:
                    doc.add_paragraph(f"• {s_item}", style='List Bullet')

                buf = BytesIO()
                doc.save(buf)
                st.download_button("📥 Scarica Report", buf.getvalue(), "Report_DIMOS_Multi.docx")
