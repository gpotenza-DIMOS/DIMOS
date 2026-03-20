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
    
    st.header("📈 Plotter DIMOS - Gestione Multisensore Completa")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
    
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Foglio Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    # --- 1. MAPPATURA ESPLOSA (MULTISENSORE) ---
    # Questa sezione scansiona TUTTE le colonne per ogni ID Web trovato
    anagrafica = {}
    
    for c_idx in range(1, df_name.shape[1]):
        dl_label = str(df_name.iloc[0, c_idx]).strip()
        sens_label = str(df_name.iloc[1, c_idx]).strip()
        web_id = str(df_name.iloc[2, c_idx]).strip()
        
        if dl_label not in anagrafica: anagrafica[dl_label] = {}
        if sens_label not in anagrafica[dl_label]: anagrafica[dl_label][sens_label] = {}
        
        # Cerchiamo tutte le colonne che iniziano con il web_id (es. CO_9277 CL_01)
        for col_data in df.columns:
            if col_data.startswith(web_id):
                # Estraiamo la grandezza specifica (es. X [°], LM [m])
                # Puliamo l'etichetta rimuovendo il prefisso web
                grandezza = col_data.replace(web_id, "").strip().lstrip('_')
                if not grandezza and "[" in col_data:
                    grandezza = re.search(r'\[.*?\]', col_data).group(0)
                
                # Salviamo la colonna reale nel dizionario delle grandezze del sensore
                anagrafica[dl_label][sens_label][grandezza] = col_data

    # --- 2. SIDEBAR FILTRI (GAUSS E ZERI) ---
    st.sidebar.header("⚙️ Parametri Analisi")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri", value=True)
    use_gauss = st.sidebar.checkbox("Filtro Gauss (Sigma)", value=True)
    sigma_val = st.sidebar.slider("Livello Sigma", 1.0, 5.0, 2.0, 0.1)
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 3. SELEZIONE MULTIPLA ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Seleziona Periodo", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: 
        s_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    
    opts_s = [f"{d} | {s}" for d in s_dls for s in anagrafica[d].keys()]
    with c2: 
        s_sens = st.multiselect("Sensori", opts_s)
    
    # RACCOLTA GRANDEZZE: Qui ora appariranno TUTTE le 8 opzioni per SD_301
    opts_g = set()
    for it in s_sens:
        d, s = it.split(" | ")
        opts_g.update(anagrafica[d][s].keys())
    
    with c3: 
        s_grands = st.multiselect("Grandezze Fisiche", sorted(list(opts_g)))

    # --- 4. MOTORE DI CALCOLO ---
    def get_clean_series(col):
        y = df_f[col].copy()
        if clean_zeros: y = y.replace(0, np.nan)
        if use_gauss and y.notna().sum() > 5:
            m, sd = y.mean(), y.std()
            y = y.mask(abs(y - m) > (sigma_val * sd), np.nan)
        return y.interpolate(limit_direction='both')

    # --- 5. GRAFICO ---
    fig = go.Figure()
    if s_sens and s_grands:
        for it in s_sens:
            d, s = it.split(" | ")
            for g in s_grands:
                if g in anagrafica[d][s]:
                    c_real = anagrafica[d][s][g]
                    y_p = get_clean_series(c_real)
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_p, name=f"{s} - {g}"))
                    
                    if grado_poly > 0:
                        x_n = np.arange(len(y_p))
                        v = y_p.notna()
                        if v.any():
                            p = np.poly1d(np.polyfit(x_n[v], y_p[v], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_n), 
                                                   name=f"Trend {s} {g}", line=dict(dash='dot')))

        st.plotly_chart(fig, use_container_width=True)

        # --- 6. COMANDI DI PRODUZIONE STAMPE (REPLICANO LA VISUALIZZAZIONE) ---
        st.divider()
        st.subheader("💾 Comandi di Stampa (Produzione Report)")
        cw, ce = st.columns(2)

        with cw:
            if st.button("📝 PRODUCI REPORT WORD"):
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                doc.add_paragraph(f"Visualizzazione speculare: Gauss {sigma_val}, Zeri {clean_zeros}")
                # Il grafico nel Word è esattamente lo stesso visualizzato
                img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
                doc.add_picture(img_io, width=Inches(6.2))
                
                target_w = BytesIO(); doc.save(target_w)
                st.download_button("📥 Scarica Report Word", target_w.getvalue(), "Report.docx")

        with ce:
            if st.button("📊 PRODUCI EXCEL DATI"):
                # Excel speculare con solo i dati e i filtri scelti a video
                df_out = pd.DataFrame({'Data Ora': df_f['Data e Ora']})
                for it in s_sens:
                    d, s = it.split(" | ")
                    for g in s_grands:
                        if g in anagrafica[d][s]:
                            df_out[f"{s}_{g}"] = get_clean_series(anagrafica[d][s][g])
                
                target_e = BytesIO()
                df_out.to_excel(target_e, index=False)
                st.download_button("📥 Scarica Dati Excel", target_e.getvalue(), "Dati_Stampa.xlsx")
