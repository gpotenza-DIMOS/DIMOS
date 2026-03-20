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
    
    st.header("📈 Plotter DIMOS - Visualizzazione e Stampa Speculare")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. MAPPATURA NOMI (RIGIDA DA FOGLIO NAME) ---
    anagrafica = {}
    if "NAME" in xls.sheet_names:
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        # Riga 0: DL, Riga 1: Sensore, Riga 2: Nome Web (es. CO_9277 CL_01)
        for c_idx in range(1, df_name.shape[1]):
            dl = str(df_name.iloc[0, c_idx]).strip()
            sens = str(df_name.iloc[1, c_idx]).strip()
            web_id = str(df_name.iloc[2, c_idx]).strip()
            
            if dl not in anagrafica: anagrafica[dl] = {}
            if sens not in anagrafica[dl]: anagrafica[dl][sens] = {"web_id": web_id, "cols": {}}
    else:
        st.error("Manca il foglio 'NAME' per la mappatura."); return

    # --- 2. CARICAMENTO DATI ---
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    # Cerchiamo le colonne fisiche che contengono il web_id
    for dl in anagrafica:
        for sens in anagrafica[dl]:
            wid = anagrafica[dl][sens]["web_id"]
            for c in df.columns:
                if wid in c: # Corrispondenza trovata
                    unit = re.search(r'\[.*?\]', c).group(0) if '[' in c else ""
                    grandezza = c.replace(wid, "").strip().lstrip('_')
                    if not grandezza: grandezza = unit
                    anagrafica[dl][sens]["cols"][grandezza] = c

    # --- 3. FILTRI SIDEBAR (GAUSS & ZERI) ---
    st.sidebar.header("⚙️ Pulizia Dati")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri", value=True)
    use_gauss = st.sidebar.checkbox("Filtro Gauss (Sigma)", value=True)
    sigma_val = st.sidebar.slider("Sigma", 1.0, 5.0, 2.0, 0.1)
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 4. SELEZIONE MULTIPLA ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Periodo", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: s_dls = st.multiselect("Datalogger", sorted(anagrafica.keys()))
    
    opts_s = [f"{d} | {s}" for d in s_dls for s in anagrafica[d].keys()]
    with c2: s_sens = st.multiselect("Sensori", opts_s)
    
    opts_g = set()
    for it in s_sens:
        d, s = it.split(" | ")
        opts_g.update(anagrafica[d][s]["cols"].keys())
    with c3: s_grands = st.multiselect("Grandezze", sorted(list(opts_g)))

    # --- 5. ELABORAZIONE E VISUALIZZAZIONE ---
    def process(col):
        y = df_f[col].copy()
        if clean_zeros: y = y.replace(0, np.nan)
        if use_gauss and y.notna().sum() > 5:
            m, sd = y.mean(), y.std()
            y = y.mask(abs(y - m) > (sigma_val * sd), np.nan)
        return y.interpolate(limit_direction='both')

    fig = go.Figure()
    if s_sens and s_grands:
        for it in s_sens:
            d, s = it.split(" | ")
            for g in s_grands:
                if g in anagrafica[d][s]["cols"]:
                    c_name = anagrafica[d][s]["cols"][g]
                    y_f = process(c_name)
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_f, name=f"{s} - {g}"))
                    
                    if grado_poly > 0:
                        x_n = np.arange(len(y_f))
                        val = y_f.notna()
                        if val.any():
                            p = np.poly1d(np.polyfit(x_n[val], y_f[val], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_n), name=f"Trend {s} {g}", line=dict(dash='dot')))

        st.plotly_chart(fig, use_container_width=True)

        # --- 6. COMANDI DI STAMPA SPECULARE ---
        st.divider()
        st.subheader("💾 Esportazione Speculare (Word / Excel)")
        col_w, col_e = st.columns(2)

        with col_w:
            if st.button("📝 PRODUCI REPORT WORD"):
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                doc.add_paragraph(f"Configurazione: Gauss={sigma_val}, Zeri={clean_zeros}")
                # Inserisce esattamente il grafico visualizzato sopra
                img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
                doc.add_picture(img_io, width=Inches(6.2))
                # Tabella riassuntiva dei sensori inclusi
                table = doc.add_table(rows=1, cols=2); table.style = 'Table Grid'
                table.rows[0].cells[0].text = 'Sensore'; table.rows[0].cells[1].text = 'Datalogger'
                for it in s_sens:
                    d, s = it.split(" | ")
                    row = table.add_row().cells
                    row[0].text = s; row[1].text = d
                
                out_w = BytesIO(); doc.save(out_w)
                st.download_button("📥 Scarica Word", out_w.getvalue(), "Report.docx")

        with col_e:
            if st.button("📊 PRODUCI EXCEL DATI"):
                # Crea un Excel con solo le colonne selezionate e pulite
                df_excel = pd.DataFrame({'Data Ora': df_f['Data e Ora']})
                for it in s_sens:
                    d, s = it.split(" | ")
                    for g in s_grands:
                        if g in anagrafica[d][s]["cols"]:
                            col_c = anagrafica[d][s]["cols"][g]
                            df_excel[f"{s}_{g}"] = process(col_c)
                
                out_e = BytesIO()
                df_excel.to_excel(out_e, index=False)
                st.download_button("📥 Scarica Excel", out_e.getvalue(), "Dati_Selezionati.xlsx")
