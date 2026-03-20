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
    col_l, _ = st.columns([1, 2])
    with col_l:
        if os.path.exists("logo_dimos.jpg"): st.image("logo_dimos.jpg", width=300)
    
    st.header("📈 Sistema Plotter DIMOS - Analisi Completa e Trend")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. MAPPATURA GRANULARE (NAME LAYER) ---
    anagrafica = {} 
    if "NAME" in xls.sheet_names:
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        for c_idx in range(1, df_name.shape[1]):
            dl = str(df_name.iloc[0, c_idx]).strip()
            sens = str(df_name.iloc[1, c_idx]).strip()
            full_web = str(df_name.iloc[2, c_idx]).strip()
            
            if dl == "nan" or full_web == "nan": continue
            if dl not in anagrafica: anagrafica[dl] = {}
            if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
            
            # Identifichiamo la grandezza (es. X [°], LM [m])
            grandezza = full_web.split("_")[-1] if "_" in full_web else full_web
            anagrafica[dl][sens][grandezza] = full_web
    else:
        st.error("Foglio NAME non trovato. Verificare il file."); return

    # --- 2. CARICAMENTO DATI ---
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    # --- 3. SIDEBAR: FILTRI E TREND ---
    st.sidebar.header("🛠️ Strumenti di Analisi")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri", value=True)
    use_gauss = st.sidebar.checkbox("Filtro Gaussiano", value=True)
    sigma_val = st.sidebar.slider("Sigma Gauss", 1.0, 5.0, 2.0, 0.1)
    
    st.sidebar.divider()
    st.sidebar.subheader("📈 Curva di Tendenza")
    grado_poly = st.sidebar.selectbox("Grado Polinomiale", [0, 2, 3, 4], 
                                     format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 4. SELEZIONE MULTIPLA ---
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Periodo", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: sel_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    
    opts_s = [f"{d} | {s}" for d in sel_dls for s in anagrafica[d].keys()]
    with c2: sel_sens = st.multiselect("Sensori", opts_s)
    
    opts_g = set()
    for it in sel_sens:
        d, s = it.split(" | ")
        opts_g.update(anagrafica[d][s].keys())
    with c3: sel_grands = st.multiselect("Grandezze Fisiche", sorted(list(opts_g)))

    # --- 5. ELABORAZIONE E CALCOLO TREND ---
    def process_and_trend(col):
        y = df_f[col].copy()
        if clean_zeros: y = y.replace(0, np.nan)
        if use_gauss and y.notna().sum() > 5:
            m, s = y.mean(), y.std()
            y = y.mask(abs(y - m) > (sigma_val * s), np.nan)
        y_clean = y.interpolate(limit_direction='both')
        
        y_trend = None
        if grado_poly > 0 and y_clean.notna().any():
            x_idx = np.arange(len(y_clean))
            mask = y_clean.notna()
            coeffs = np.polyfit(x_idx[mask], y_clean[mask], grado_poly)
            p = np.poly1d(coeffs)
            y_trend = pd.Series(p(x_idx), index=y_clean.index)
            
        return y_clean, y_trend

    # --- 6. GRAFICO ---
    fig = go.Figure()
    if sel_sens and sel_grands:
        for it in sel_sens:
            d, s = it.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]:
                    c_real = anagrafica[d][s][g]
                    y_val, y_tr = process_and_trend(c_real)
                    
                    # Linea Dati
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_val, name=f"{s} - {g}"))
                    # Linea Trend
                    if y_tr is not None:
                        fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_tr, 
                                               name=f"Trend {s} ({g})", 
                                               line=dict(dash='dash', width=2)))

        fig.update_layout(template="plotly_white", height=700, hovermode="x unified",
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

        # --- 7. STAMPE SPECULARI ---
        st.divider()
        st.subheader("💾 Produzione File di Stampa")
        cw, ce = st.columns(2)

        with cw:
            if st.button("📝 PRODUCI REPORT WORD"):
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                doc.add_paragraph(f"Analisi con Trend Polinomiale Grado {grado_poly}")
                img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
                doc.add_picture(img_io, width=Inches(6.2))
                buf_w = BytesIO(); doc.save(buf_w)
                st.download_button("📥 Scarica Word", buf_w.getvalue(), "Report.docx")

        with ce:
            if st.button("📊 PRODUCI EXCEL STAMPA"):
                df_out = pd.DataFrame({'Data Ora': df_f['Data e Ora']})
                for it in sel_sens:
                    d, s = it.split(" | ")
                    for g in sel_grands:
                        if g in anagrafica[d][s]:
                            y_v, y_t = process_and_trend(anagrafica[d][s][g])
                            df_out[f"{s}_{g}"] = y_v
                            if y_t is not None: df_out[f"Trend_{s}_{g}"] = y_t
                buf_e = BytesIO()
                df_out.to_excel(buf_e, index=False)
                st.download_button("📥 Scarica Excel", buf_e.getvalue(), "Dati.xlsx")
