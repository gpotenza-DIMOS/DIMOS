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
    # Logo DIMOS
    col_l, _ = st.columns([1, 2])
    with col_l:
        if os.path.exists("logo_dimos.jpg"): st.image("logo_dimos.jpg", width=300)
    
    st.header("📈 Plotter Multisensore Professionale")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
    
    # Selezione foglio dati
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Foglio Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    # --- 1. MAPPATURA DINAMICA (ESPLOSIONE MULTISENSORE) ---
    # Struttura: { "C15_302S": { "SD_301": { "X [°]": "CO_9277 CL_01_X [°]", ... } } }
    anagrafica = {}
    
    # Leggiamo il foglio NAME (Riga 0: DL, Riga 1: Sensore, Riga 2: WebID)
    for c_idx in range(1, df_name.shape[1]):
        dl_label = str(df_name.iloc[0, c_idx]).strip()
        sens_label = str(df_name.iloc[1, c_idx]).strip()
        web_prefix = str(df_name.iloc[2, c_idx]).strip()
        
        if dl_label not in anagrafica: anagrafica[dl_label] = {}
        if sens_label not in anagrafica[dl_label]: anagrafica[dl_label][sens_label] = {}
        
        # Scansione di TUTTE le colonne per trovare i parametri del multisensore
        for col in df.columns:
            if web_prefix in col:
                # Estraiamo l'etichetta della grandezza (es. X [°])
                # Puliamo il nome colonna togliendo il prefisso web
                label_grandezza = col.replace(web_prefix, "").strip().lstrip('_')
                if not label_grandezza and "[" in col:
                    label_grandezza = re.search(r'\[.*?\]', col).group(0)
                
                # Salviamo la corrispondenza
                anagrafica[dl_label][sens_label][label_grandezza] = col

    # --- 2. SIDEBAR ANALISI (GAUSS E ZERI) ---
    st.sidebar.header("⚙️ Parametri Analisi")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri (Errori)", value=True)
    use_gauss = st.sidebar.checkbox("Filtro Gauss (Sigma)", value=True)
    sigma_val = st.sidebar.slider("Sensibilità Gauss", 1.0, 5.0, 2.0, 0.1)
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 3. SELEZIONE MULTIPLA ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Intervallo Temporale", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: 
        sel_dls = st.multiselect("1. Datalogger", sorted(anagrafica.keys()))
    
    opts_s = [f"{d} | {s}" for d in sel_dls for s in anagrafica[d].keys()]
    with c2: 
        sel_sens = st.multiselect("2. Sensori", opts_s)
    
    opts_g = set()
    for item in sel_sens:
        d, s = item.split(" | ")
        opts_g.update(anagrafica[d][s].keys())
    
    with c3: 
        # Qui ora vedrai TUTTE le grandezze (X, Y, Z, T1, T2, LI, LQ, LM)
        sel_grands = st.multiselect("3. Grandezze Fisiche", sorted(list(opts_g)))

    # --- 4. ELABORAZIONE ---
    def process_series(col_name):
        y = df_f[col_name].copy()
        if clean_zeros: y = y.replace(0, np.nan)
        if use_gauss and y.notna().sum() > 5:
            m, sd = y.mean(), y.std()
            y = y.mask(abs(y - m) > (sigma_val * sd), np.nan)
        return y.interpolate(limit_direction='both')

    # --- 5. VISUALIZZAZIONE ---
    fig = go.Figure()
    if sel_sens and sel_grands:
        for item in sel_sens:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]:
                    col_target = anagrafica[d][s][g]
                    y_proc = process_series(col_target)
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_proc, name=f"{s} - {g}"))
                    
                    if grado_poly > 0:
                        x_n = np.arange(len(y_proc))
                        valid = y_proc.notna()
                        if valid.any():
                            coeffs = np.polyfit(x_n[valid], y_proc[valid], grado_poly)
                            p = np.poly1d(coeffs)
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_n), 
                                                   name=f"Trend {s} {g}", line=dict(dash='dot')))

        st.plotly_chart(fig, use_container_width=True)

        # --- 6. COMANDI DI STAMPA SPECULARE ---
        st.divider()
        st.subheader("💾 Esportazione Speculare (Stesso contenuto del grafico)")
        cw, ce = st.columns(2)

        with cw:
            if st.button("📝 PRODUCI REPORT WORD"):
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                doc.add_paragraph(f"Periodo: {sel_range[0]} - {sel_range[1]}")
                doc.add_paragraph(f"Parametri: Gauss={sigma_val}, Rimozione Zeri={clean_zeros}")
                
                # Cattura esattamente il grafico sopra
                img_data = pio.to_image(fig, format="png", width=1100, height=550)
                doc.add_picture(BytesIO(img_data), width=Inches(6.3))
                
                target_w = BytesIO(); doc.save(target_w)
                st.download_button("📥 Scarica Word", target_w.getvalue(), "Report_DIMOS.docx")

        with ce:
            if st.button("📊 PRODUCI EXCEL DATI"):
                # Crea un excel con solo le colonne e i filtri applicati a video
                df_out = pd.DataFrame({'Data Ora': df_f['Data e Ora']})
                for item in sel_sens:
                    d, s = item.split(" | ")
                    for g in sel_grands:
                        if g in anagrafica[d][s]:
                            df_out[f"{s}_{g}"] = process_series(anagrafica[d][s][g])
                
                target_e = BytesIO()
                df_out.to_excel(target_e, index=False)
                st.download_button("📥 Scarica Excel", target_e.getvalue(), "Dati_Selezionati.xlsx")
