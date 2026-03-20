import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# Importiamo le librerie per Word come nel modulo elettrolivelle
try:
    from docx import Document
    from docx.shared import Inches
    import plotly.io as pio
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def run_plotter():
    st.header("📈 Analisi e Reportistica Sensori")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="pl_up")
    if not file_input:
        st.info("Carica un file per iniziare.")
        return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. COSTRUZIONE ANAGRAFICA GERARCHICA ---
    # Struttura: { 'Datalogger': { 'Sensore': { 'Grandezza': 'NomeColonna' } } }
    anagrafica = {}
    
    # Proviamo a leggere il foglio NAME
    mapping_name = None
    if "NAME" in xls.sheet_names:
        mapping_name = pd.read_excel(xls, sheet_name="NAME", header=None)

    # Identifichiamo il foglio dati (flegrei o simile)
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    
    if 'Data e Ora' not in df.columns:
        st.error("Colonna 'Data e Ora' mancante.")
        return
    
    time_col = pd.to_datetime(df['Data e Ora'])

    # Analisi colonne per popolare l'anagrafica
    cols_sensori = [c for c in df.columns if '[' in c]
    
    for col in cols_sensori:
        datalogger, sensore, grandezza = "Generico", "Ignoto", col
        
        # Caso A: C'è il foglio NAME per la mappatura
        if mapping_name is not None:
            # Cerchiamo la colonna nel foglio NAME che corrisponde al nome web in riga 3
            match_col = None
            for c_idx in range(1, mapping_name.shape[1]):
                if str(mapping_name.iloc[2, c_idx]).strip() in col:
                    match_col = c_idx
                    break
            
            if match_col:
                datalogger = str(mapping_name.iloc[0, match_col]).strip()
                sensore = str(mapping_name.iloc[1, match_col]).strip()
        
        # Caso B: Non c'è NAME o non c'è match -> Estrazione da stringa web
        # "CO_9277 CL_01_X [°]" -> DL: CO_9277, SENS: CL_01, PARAM: X [°]
        if datalogger == "Generico":
            parts = col.split(' ')
            datalogger = parts[0]
            # Cerchiamo l'unita tra parentesi
            unita = re.search(r'\[(.*?)\]', col).group(0) if '[' in col else ""
            # Il resto è il nome sensore + parametro
            sens_web = col.replace(datalogger, "").replace(unita, "").strip()
            # Gestione multisensore: CL_01_X -> Sensore CL_01, Parametro X
            if '_' in sens_web:
                s_parts = sens_web.split('_')
                sensore = "_".join(s_parts[:-1]) if len(s_parts) > 1 else s_parts[0]
            else:
                sensore = sens_web

        grandezza = col.split(sensore)[-1].strip() if sensore in col else col
        
        # Popolamento dizionario
        if datalogger not in anagrafica: anagrafica[datalogger] = {}
        if sensore not in anagrafica[datalogger]: anagrafica[datalogger][sensore] = {}
        anagrafica[datalogger][sensore][grandezza] = col

    # --- 2. INTERFACCIA DI SELEZIONE A CASCATA ---
    st.divider()
    t1, t2 = st.tabs(["📊 Visualizzazione", "🖨️ Report Word"])

    with t1:
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_dl = st.selectbox("1. Seleziona Datalogger", sorted(anagrafica.keys()))
        with c2:
            sel_sens = st.selectbox("2. Seleziona Sensore", sorted(anagrafica[sel_dl].keys()))
        with c3:
            # Qui l'utente sceglie i parametri (X, Y, T1...)
            opzioni_grandezze = anagrafica[sel_dl][sel_sens]
            sel_grands = st.multiselect("3. Grandezze Fisiche", list(opzioni_grandezze.keys()), default=list(opzioni_grandezze.keys())[0])

        if sel_grands:
            fig = go.Figure()
            for g in sel_grands:
                col_name = opzioni_grandezze[g]
                fig.add_trace(go.Scatter(x=time_col, y=df[col_name], name=f"{sel_sens} - {g}"))
            
            fig.update_layout(
                title=f"Trend {sel_sens} ({sel_dl})",
                xaxis_title="Tempo",
                template="plotly_white",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        st.subheader("Generazione Report Professionale")
        dl_report = st.multiselect("Seleziona Datalogger per Report", sorted(anagrafica.keys()))
        
        if st.button("🚀 GENERA DOCUMENTO WORD"):
            if not DOCX_AVAILABLE:
                st.error("Libreria docx non trovata.")
            else:
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO SENSORI', 0)
                
                for dl in dl_report:
                    doc.add_heading(f'DATALOGGER: {dl}', level=1)
                    for sens in anagrafica[dl]:
                        doc.add_heading(f'Sensore: {sens}', level=2)
                        
                        # Creiamo un grafico per ogni sensore con tutte le sue grandezze
                        fig_r = go.Figure()
                        for g_label, col_data in anagrafica[dl][sens].items():
                            fig_r.add_trace(go.Scatter(x=time_col, y=df[col_data], name=g_label))
                        
                        fig_r.update_layout(title=f"Andamento {sens}", width=800, height=400)
                        
                        # Salvataggio immagine per Word
                        img_io = BytesIO(pio.to_image(fig_r, format="png"))
                        doc.add_picture(img_io, width=Inches(6))
                        doc.add_paragraph(f"Dati estratti dal foglio {sel_sheet}")
                
                target = BytesIO()
                doc.save(target)
                st.download_button("📥 Scarica Report", target.getvalue(), "Report_Sensori.docx")

# Inserisci nel main:
# if page == "pl": run_plotter()
