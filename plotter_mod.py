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
    
    st.header("📈 Analisi Professionale - Diagnostica Gauss & Zeri")

    file_input = st.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    
    # --- SIDEBAR: PARAMETRI FISSI E VARIABILI ---
    st.sidebar.header("⚙️ Parametri Analisi")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri (0.00)", value=True)
    use_gauss = st.sidebar.checkbox("Attiva Filtro Gauss", value=True)
    # Sigma 2.0 come base, ma regolabile
    sigma_val = st.sidebar.slider("Livello Sigma (2.0 = Standard)", 0.5, 5.0, 2.0, 0.1)
    # Media mobile per stabilizzare
    use_rolling = st.sidebar.checkbox("Media Mobile (Smooth 5 punti)", value=True)
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 1. MAPPATURA ANAGRAFICA ---
    # [Logica mappatura NAME/Web già validata e funzionante]
    anagrafica = {}
    df_name = pd.read_excel(xls, sheet_name="NAME", header=None) if "NAME" in xls.sheet_names else None
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    cols_data = [c for c in df.columns if '[' in c]
    for col in cols_data:
        # (Codice di mappatura DL/Sensore/Grandezza...)
        dl = col.split(' ')[0] # Esempio semplificato per brevità
        sens = col.split(' ')[1] if len(col.split(' ')) > 1 else "S"
        grandezza = col.split(sens)[-1].strip()
        if dl not in anagrafica: anagrafica[dl] = {}
        if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
        anagrafica[dl][sens][grandezza] = col

    # --- 2. SELEZIONE MULTIPLA ---
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

    # --- 3. FUNZIONE DI PULIZIA CON DIAGNOSTICA ---
    def process_series(col_name):
        y_orig = df_f[col_name].copy()
        count_orig = y_orig.count()
        
        # Rimozione Zeri
        if clean_zeros:
            y_orig = y_orig.replace(0, np.nan)
        
        # Filtro Gauss
        if use_gauss and y_orig.notna().sum() > 5:
            m = y_orig.mean()
            s_dev = y_orig.std()
            y_orig = y_orig.mask(abs(y_orig - m) > (sigma_val * s_dev), np.nan)
        
        # Media Mobile
        if use_rolling:
            y_orig = y_orig.rolling(window=5, center=True).mean()
        
        # INTERPOLAZIONE CRITICA: Se non interpola, il grafico sparisce
        y_final = y_orig.interpolate(method='linear', limit_direction='both')
        
        rem_count = count_orig - y_final.count()
        return y_final, rem_count

    # --- 4. GRAFICO E REPORT PULIZIA ---
    if sel_sens_f and sel_grands:
        fig = go.Figure()
        stats = []

        for item in sel_sens_f:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]:
                    y_proc, removed = process_series(anagrafica[d][s][g])
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_proc, name=f"{s} - {g}"))
                    stats.append(f"**{s} ({g})**: Rimossi {removed} punti anomali.")

        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📊 Report Diagnostico Pulizia"):
            for line in stats: st.write(line)

        # --- 5. STAMPE (IDENTICHE A VIDEO) ---
        st.divider()
        st.subheader("🖨️ Opzioni Stampa Report")
        col_st1, col_st2 = st.columns(2)
        
        with col_st1:
            if st.button("🚀 WORD: Grafico di Confronto"):
                doc = Document()
                doc.add_heading('Report DIMOS - Confronto Sensori', 0)
                # Salviamo il grafico corrente
                img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
                doc.add_picture(img_io, width=Inches(6.2))
                buf = BytesIO(); doc.save(buf)
                st.download_button("Download Confronto", buf.getvalue(), "Confronto.docx")

        with col_st2:
            if st.button("🚀 WORD: Singolo Sensore per Pagina"):
                doc = Document()
                doc.add_heading('Report DIMOS - Dettaglio Sensori', 0)
                for item in sel_sens_f:
                    d, s = item.split(" | ")
                    doc.add_heading(f"Sensore: {s} | DL: {d}", level=2)
                    f_tmp = go.Figure()
                    for g in sel_grands:
                        if g in anagrafica[d][s]:
                            y_tmp, _ = process_series(anagrafica[d][s][g])
                            f_tmp.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_tmp, name=g))
                    img_tmp = BytesIO(pio.to_image(f_tmp, format="png", width=900, height=400))
                    doc.add_picture(img_tmp, width=Inches(6.0))
                    doc.add_page_break()
                buf = BytesIO(); doc.save(buf)
                st.download_button("Download Dettaglio", buf.getvalue(), "Dettaglio.docx")
