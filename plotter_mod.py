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
    # --- LOGO E TITOLO ---
    col_logo, _ = st.columns([1, 2])
    with col_logo:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", width=300)
    st.header("📈 Analisi Temporale e Multisensore")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="plot_up")
    if not file_input:
        st.info("Carica un file Excel per iniziare.")
        return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. COSTRUZIONE ANAGRAFICA (DA LAYER NAME O WEB) ---
    # Struttura: { "Datalogger": { "Sensore": { "Grandezza Fisica": "Nome Colonna Originale" } } }
    anagrafica = {}
    
    # Carico il layer NAME se esiste
    df_name = None
    if "NAME" in xls.sheet_names:
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)

    # Scelta foglio dati
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Foglio Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    
    if 'Data e Ora' not in df.columns:
        st.error("Colonna 'Data e Ora' non trovata.")
        return
    
    time_col = pd.to_datetime(df['Data e Ora'])

    # Popolamento Gerarchico
    cols_data = [c for c in df.columns if '[' in c]
    for col in cols_data:
        dl, sens, grandezza = None, None, None
        
        # Caso 1: Uso il foglio NAME (Riga 1: DL, Riga 2: Sens, Riga 3: Web)
        if df_name is not None:
            for c_idx in range(1, df_name.shape[1]):
                nome_web_r3 = str(df_name.iloc[2, c_idx]).strip()
                if nome_web_r3 in col:
                    dl = str(df_name.iloc[0, c_idx]).strip()
                    sens = str(df_name.iloc[1, c_idx]).strip()
                    # La grandezza è ciò che resta dopo il nome web nel nome colonna
                    grandezza = col.split(nome_web_r3)[-1].strip()
                    if not grandezza: # Caso sensore singolo
                        grandezza = re.search(r'\[.*?\]', col).group(0) if '[' in col else "Dato"
                    break
        
        # Caso 2: Estrazione diretta se NAME non c'è o non ha trovato match
        if not dl:
            parts = col.split(' ')
            dl = parts[0] # CO_9286
            unita = re.search(r'\[.*?\]', col).group(0) if '[' in col else ""
            sens_web = col.replace(dl, "").replace(unita, "").strip()
            
            if '_' in sens_web: # Multisensore CL_01_X
                s_parts = sens_web.split('_')
                sens = "_".join(s_parts[:-1]) if len(s_parts) > 1 else s_parts[0]
                grandezza = s_parts[-1] + " " + unita
            else: # Sensore singolo VAR5
                sens = sens_web
                grandezza = unita

        # Pulizia finale grandezza per avere solo "X [°]", "T1 [°C]", ecc.
        grandezza = grandezza.lstrip('_').strip()

        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        anagrafica[dl][sens][grandezza] = col

    # --- 2. FILTRO TEMPORALE (SLIDER DINAMICO) ---
    st.divider()
    min_d, max_d = time_col.min(), time_col.max()
    sel_range = st.slider("Seleziona Intervallo Temporale", min_d.to_pydatetime(), max_d.to_pydatetime(), (min_d.to_pydatetime(), max_d.to_pydatetime()))
    df_plot = df[(time_col >= sel_range[0]) & (time_col <= sel_range[1])].copy()

    # --- 3. SELEZIONE A CASCATA ---
    c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1])
    with c1:
        sel_dl = st.selectbox("Datalogger", sorted(anagrafica.keys()))
    with c2:
        sel_sens = st.selectbox("Sensore", sorted(anagrafica[sel_dl].keys()))
    with c3:
        lista_grandi = anagrafica[sel_dl][sel_sens]
        sel_grandi = st.multiselect("Grandezze Fisiche", list(lista_grandi.keys()))
    with c4:
        grado_poly = st.selectbox("Curva di Tendenza", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Polinomiale Gr. {x}")

    # --- 4. GRAFICO E STAMPA ---
    if sel_grandi:
        fig = go.Figure()
        for g in sel_grandi:
            real_col = lista_grandi[g]
            y_vals = df_plot[real_col].interpolate()
            x_vals = df_plot['Data e Ora']
            
            # Traccia Dati
            fig.add_trace(go.Scatter(x=x_vals, y=y_vals, name=f"{g}"))
            
            # Traccia Trend Polinomiale
            if grado_poly > 0:
                x_num = np.arange(len(y_vals))
                mask = ~y_vals.isna()
                if mask.any():
                    z = np.polyfit(x_num[mask], y_vals[mask], grado_poly)
                    p = np.poly1d(z)
                    fig.add_trace(go.Scatter(x=x_vals, y=p(x_num), name=f"Trend {g}", line=dict(dash='dot')))

        fig.update_layout(template="plotly_white", hovermode="x unified", height=600)
        st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 GENERA REPORT WORD"):
            if DOCX_AVAILABLE:
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO - DIMOS', 0)
                doc.add_heading(f'Datalogger: {sel_dl} | Sensore: {sel_sens}', level=1)
                
                img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
                doc.add_picture(img_io, width=Inches(6.2))
                
                out = BytesIO()
                doc.save(out)
                st.download_button("📥 Scarica Word", out.getvalue(), f"Report_{sel_sens}.docx")
