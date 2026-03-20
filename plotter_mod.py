import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    import plotly.io as pio
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def run_plotter():
    # --- LOGO DIMOS ---
    col_logo, _ = st.columns([1, 2])
    with col_logo:
        if os.path.exists("logo_dimos.jpg"):
            st.image("logo_dimos.jpg", width=300)
    
    st.header("📈 Monitoraggio Sensori - Analisi Temporale")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="pl_up")
    if not file_input:
        st.info("In attesa del file Excel...")
        return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. MAPPATURA ANAGRAFICA (Foglio NAME) ---
    anagrafica = {}
    mapping_name = None
    if "NAME" in xls.sheet_names:
        mapping_name = pd.read_excel(xls, sheet_name="NAME", header=None)

    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    
    if 'Data e Ora' not in df.columns:
        st.error("Colonna 'Data e Ora' mancante.")
        return
    
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])
    time_col = df['Data e Ora']

    # --- 2. LOGICA DI ESTRAZIONE RIGIDA ---
    cols_sensori = [c for c in df.columns if '[' in c]
    for col in cols_sensori:
        dl_nome, sens_nome = "Generico", "Ignoto"
        
        # Match con foglio NAME (Riga 3 = Nome Web)
        if mapping_name is not None:
            for c_idx in range(1, mapping_name.shape[1]):
                nome_web_r3 = str(mapping_name.iloc[2, c_idx]).strip()
                if nome_web_r3 in col:
                    dl_nome = str(mapping_name.iloc[0, c_idx]).strip()
                    sens_nome = str(mapping_name.iloc[1, c_idx]).strip()
                    break
        
        # Se non trova in NAME, estrae da stringa
        if dl_nome == "Generico":
            dl_nome = col.split(' ')[0]
            sens_nome = col.split(' ')[1] if len(col.split(' ')) > 1 else "SENS"

        # Pulizia Grandezza Fisica (Solo X [°], Y [°], etc.)
        # Estraiamo l'etichetta finale (es: _X [°] o VAR5 [mm])
        grandezza_pulita = col.split(sens_nome)[-1].strip() if sens_nome in col else col
        if '_' in grandezza_pulita and grandezza_pulita.startswith('_'):
            grandezza_pulita = grandezza_pulita[1:] # Rimuove l'underscore iniziale se presente

        if dl_nome not in anagrafica: anagrafica[dl_nome] = {}
        if sens_nome not in anagrafica[dl_nome]: anagrafica[dl_nome][sens_nome] = {}
        anagrafica[dl_nome][sens_nome][grandezza_pulita] = col

    # --- 3. BARRA DINAMICA SINISTRA-DESTRA (SLIDER DATE) ---
    st.divider()
    min_date = time_col.min().to_pydatetime()
    max_date = time_col.max().to_pydatetime()
    
    sel_date = st.slider("Filtro Intervallo Temporale", 
                         min_value=min_date, 
                         max_value=max_date, 
                         value=(min_date, max_date))
    
    mask_time = (df['Data e Ora'] >= sel_date[0]) & (df['Data e Ora'] <= sel_date[1])
    df_filtered = df.loc[mask_time].copy()

    # --- 4. SELEZIONE GERARCHICA ---
    c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1])
    with c1:
        sel_dl = st.selectbox("Datalogger", sorted(anagrafica.keys()))
    with c2:
        sel_sens = st.selectbox("Sensore", sorted(anagrafica[sel_dl].keys()))
    with c3:
        opzioni_g = anagrafica[sel_dl][sel_sens]
        sel_grands = st.multiselect("Grandezze", list(opzioni_g.keys()))
    with c4:
        poly_degree = st.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 5. GRAFICO ---
    if sel_grands:
        fig = go.Figure()
        for g in sel_grands:
            col_raw = opzioni_g[g]
            y_data = df_filtered[col_raw]
            x_data = df_filtered['Data e Ora']
            
            # Linea Dati Reali
            fig.add_trace(go.Scatter(x=x_data, y=y_data, name=f"{g} (Dati)", mode='lines'))
            
            # Curva di Tendenza Polinomiale
            if poly_degree > 0:
                # Trasformiamo date in numeri per il fit
                x_numeric = np.arange(len(x_data))
                # Pulizia nan per il fit
                valid = ~y_data.isna()
                if valid.any():
                    coeffs = np.polyfit(x_numeric[valid], y_data[valid], poly_degree)
                    poly_func = np.poly1d(coeffs)
                    y_trend = poly_func(x_numeric)
                    fig.add_trace(go.Scatter(x=x_data, y=y_trend, 
                                           name=f"{g} Trend (Grado {poly_degree})", 
                                           line=dict(dash='dash', width=2)))

        fig.update_layout(template="plotly_white", hovermode="x unified", height=600)
        st.plotly_chart(fig, use_container_width=True)

    # --- 6. REPORT WORD ---
    st.divider()
    if st.button("🚀 GENERA REPORT WORD"):
        if DOCX_AVAILABLE:
            doc = Document()
            doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
            
            # Esempio: stampa il sensore correntemente selezionato
            doc.add_heading(f'Datalogger: {sel_dl} - Sensore: {sel_sens}', level=1)
            
            fig_report = go.Figure(fig) # Copia il grafico corrente
            fig_report.update_layout(width=800, height=450)
            img_stream = BytesIO(pio.to_image(fig_report, format="png"))
            
            doc.add_picture(img_stream, width=Inches(6.2))
            doc.add_paragraph(f"Periodo: {sel_date[0].strftime('%d/%m/%Y')} - {sel_date[1].strftime('%d/%m/%Y')}")
            
            target = BytesIO()
            doc.save(target)
            st.download_button("📥 Scarica Report", target.getvalue(), f"Report_{sel_sens}.docx")
