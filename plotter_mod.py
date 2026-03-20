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
        if os.path.exists("logo_dimos.jpg"): 
            st.image("logo_dimos.jpg", width=300)
    
    st.header("📈 Report Analitico: Gauss, Zeri e Selezioni Multiple")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    
    # --- CONFIGURAZIONE FILTRI (SIDEBAR) ---
    st.sidebar.header("🛠️ Parametri di Pulizia")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri (0.00)", value=True)
    
    # Parametro Gauss opzionale e personalizzabile
    use_gauss = st.sidebar.checkbox("Attiva Filtro Gauss (Sigma)", value=True)
    sigma_val = st.sidebar.number_input("Valore Sigma (Gauss)", min_value=1.0, max_value=5.0, value=2.0, step=0.1)
    
    use_rolling = st.sidebar.checkbox("Media Mobile (Smooth)", value=True)
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 1. MAPPATURA ANAGRAFICA ---
    anagrafica = {}
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None) if "NAME" in xls.sheet_names else None
    
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    cols_data = [c for c in df.columns if '[' in c]
    for col in cols_data:
        dl, sens, grandezza = None, None, None
        if df_name is not None:
            for c_idx in range(1, df_name.shape[1]):
                web_v = str(df_name.iloc[2, c_idx]).strip()
                if web_v in col:
                    dl = str(df_name.iloc[0, c_idx]).strip()
                    sens = str(df_name.iloc[1, c_idx]).strip()
                    grandezza = col.split(web_v)[-1].lstrip('_').strip()
                    if not grandezza: grandezza = re.search(r'\[.*?\]', col).group(0)
                    break
        if not dl:
            dl = col.split(' ')[0]
            sens = col.split(' ')[1] if len(col.split(' ')) > 1 else "SENS"
            grandezza = col.split(sens)[-1].strip()

        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        anagrafica[dl][sens][grandezza] = col

    # --- 2. FILTRI SELEZIONE MULTIPLA ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Intervallo Temporale", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: sel_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    list_s = [f"{d} | {s}" for d in sel_dls for s in anagrafica[d].keys()]
    with c2: sel_sens_f = st.multiselect("Sensori", list_s)
    list_g = set()
    for item in sel_sens_f:
        d, s = item.split(" | ")
        list_g.update(anagrafica[d][s].keys())
    with c3: sel_grands = st.multiselect("Grandezze Fisiche", sorted(list(list_g)))

    # --- 3. FUNZIONE DI PULIZIA (LOGICA OTTIMO) ---
    def get_cleaned_series(col_name):
        y = df_f[col_name].copy()
        if clean_zeros: y = y.replace(0, np.nan)
        if use_gauss and y.notna().sum() > 5:
            m, std = y.mean(), y.std()
            # Invece di cancellare, mascheriamo per l'interpolazione
            y = y.mask(abs(y - m) > (sigma_val * std), np.nan)
        if use_rolling:
            y = y.rolling(window=5, center=True).mean()
        return y.interpolate(method='linear', limit_direction='both')

    # --- 4. GRAFICO ---
    fig = go.Figure()
    if sel_sens_f and sel_grands:
        for item in sel_sens_f:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]:
                    y_p = get_cleaned_series(anagrafica[d][s][g])
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_p, name=f"{s} - {g}"))
                    
                    if grado_poly > 0:
                        x_n = np.arange(len(y_p))
                        valid = y_p.notna()
                        if valid.any():
                            p = np.poly1d(np.polyfit(x_n[valid], y_p[valid], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_n), name=f"Trend {s} {g}", line=dict(dash='dot')))

        fig.update_layout(template="plotly_white", height=700, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # --- 5. STAMPE (STESSA LOGICA DEL GRAFICO) ---
        st.divider()
        st.subheader("🖨️ Esportazione Report")
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🚀 REPORT WORD (Grafico Corrente)"):
                if DOCX_AVAILABLE:
                    doc = Document()
                    doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                    doc.add_paragraph(f"Analisi basata su filtro Gauss (Sigma: {sigma_val}) e rimozione zeri.")
                    
                    img_stream = BytesIO(pio.to_image(fig, format="png", width=1100, height=550))
                    doc.add_picture(img_stream, width=Inches(6.3))
                    
                    doc.add_heading("Dettaglio Selezione:", level=2)
                    for val in sel_sens_f: doc.add_paragraph(f"• {val}", style='List Bullet')
                    
                    target = BytesIO()
                    doc.save(target)
                    st.download_button("📥 Scarica Word", target.getvalue(), "Report_Gauss.docx")

        with col_btn2:
            if st.button("🚀 REPORT WORD (Dettagliato per Sensore)"):
                if DOCX_AVAILABLE:
                    doc = Document()
                    doc.add_heading('REPORT DETTAGLIATO DIMOS', 0)
                    for item in sel_sens_f:
                        d, s = item.split(" | ")
                        doc.add_heading(f"Sensore {s} - DL {d}", level=2)
                        fig_s = go.Figure()
                        for g in sel_grands:
                            if g in anagrafica[d][s]:
                                fig_s.add_trace(go.Scatter(x=df_f['Data e Ora'], y=get_cleaned_series(anagrafica[d][s][g]), name=g))
                        img_s = BytesIO(pio.to_image(fig_s, format="png", width=900, height=400))
                        doc.add_picture(img_s, width=Inches(6.0))
                    
                    target = BytesIO()
                    doc.save(target)
                    st.download_button("📥 Scarica Report Dettagliato", target.getvalue(), "Report_Dettaglio_Sensori.docx")
