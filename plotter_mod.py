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
    # Logo DIMOS
    col_l, _ = st.columns([1, 2])
    with col_l:
        if os.path.exists("logo_dimos.jpg"): 
            st.image("logo_dimos.jpg", width=300)
    
    st.header("📈 Plotter Avanzato: Selezione Multipla & Filtri Sigma")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    
    # --- CONFIGURAZIONE FILTRI (SIDEBAR) ---
    st.sidebar.header("🛠️ Parametri di Pulizia")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri (0.00)", value=True)
    
    # Parametro Gauss opzionale e personalizzabile
    use_gauss = st.sidebar.checkbox("Attiva Filtro Gauss (Sigma)", value=True)
    sigma_val = st.sidebar.number_input("Valore Sigma (Gauss)", min_value=1.0, max_value=5.0, value=2.0, step=0.1)
    
    # Media Mobile (ammorbidimento dati come nel file ottimo)
    use_rolling = st.sidebar.checkbox("Media Mobile (5 punti)", value=True)
    
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 1. MAPPATURA ANAGRAFICA (LAYER NAME) ---
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
        if not dl: # Fallback se NAME non c'è
            dl = col.split(' ')[0]
            unita = re.search(r'\[.*?\]', col).group(0) if '[' in col else ""
            sens_f = col.replace(dl, "").replace(unita, "").strip()
            sens = "_".join(sens_f.split('_')[:-1]) if '_' in sens_f else sens_f
            grandezza = sens_f.split('_')[-1] + " " + unita if '_' in sens_f else unita

        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        anagrafica[dl][sens][grandezza.strip()] = col

    # --- 2. FILTRI SELEZIONE MULTIPLA ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Seleziona Intervallo Temporale", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: 
        sel_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    
    list_s = [f"{d} | {s}" for d in sel_dls for s in anagrafica[d].keys()]
    with c2: 
        sel_sens_f = st.multiselect("Sensori", list_s)
    
    list_g = set()
    for item in sel_sens_f:
        d, s = item.split(" | ")
        list_g.update(anagrafica[d][s].keys())
    with c3: 
        sel_grands = st.multiselect("Grandezze Fisiche", sorted(list(list_g)))

    # --- 3. LOGICA PULIZIA & GRAFICO ---
    if sel_sens_f and sel_grands:
        fig = go.Figure()
        for item in sel_sens_f:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]:
                    col_raw = anagrafica[d][s][g]
                    y = df_f[col_raw].copy()
                    
                    # A. Rimozione Zeri
                    if clean_zeros: 
                        y = y.replace(0, np.nan)
                    
                    # B. Filtro Gauss (Sigma personalizzabile)
                    if use_gauss and y.notna().sum() > 5:
                        m, std = y.mean(), y.std()
                        y = y.mask(abs(y - m) > (sigma_val * std), np.nan)
                    
                    # C. Media Mobile (Rolling 5)
                    if use_rolling:
                        y = y.rolling(window=5, center=True).mean()
                    
                    y = y.interpolate() 
                    
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y, name=f"{s} - {g}"))
                    
                    # D. Trend Polinomiale
                    if grado_poly > 0:
                        x_n = np.arange(len(y))
                        valid = y.notna()
                        if valid.any():
                            p = np.poly1d(np.polyfit(x_n[valid], y[valid], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_n), 
                                                   name=f"Trend {s} {g}", line=dict(dash='dot')))

        fig.update_layout(template="plotly_white", height=750, hovermode="x unified",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # --- 4. STAMPE WORD (Una pagina per ogni sensore selezionato) ---
        st.divider()
        if st.button("🚀 GENERA REPORT WORD"):
            if DOCX_AVAILABLE:
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                
                for item in sel_sens_f:
                    d, s = item.split(" | ")
                    doc.add_heading(f'Datalogger: {d} - Sensore: {s}', level=1)
                    
                    # Creiamo il grafico specifico per il report
                    fig_rep = go.Figure()
                    for g in sel_grands:
                        if g in anagrafica[d][s]:
                            col_r = anagrafica[d][s][g]
                            # Applichiamo pulizia anche per la stampa
                            y_r = df_f[col_r].replace(0, np.nan)
                            if use_gauss:
                                m, std = y_r.mean(), y_r.std()
                                y_r = y_r.mask(abs(y_r - m) > (sigma_val * std), np.nan)
                            y_r = y_r.interpolate()
                            
                            fig_rep.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_r, name=g))
                    
                    fig_rep.update_layout(width=1000, height=450, template="plotly_white")
                    img_io = BytesIO(pio.to_image(fig_rep, format="png"))
                    doc.add_picture(img_io, width=Inches(6.2))
                    doc.add_page_break()

                buf = BytesIO()
                doc.save(buf)
                st.download_button("📥 Scarica Report Word", buf.getvalue(), "Report_Dimos_Plotter.docx")
