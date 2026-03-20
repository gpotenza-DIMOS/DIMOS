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
    # Logo
    col_l, _ = st.columns([1, 2])
    with col_l:
        if os.path.exists("logo_dimos.jpg"): st.image("logo_dimos.jpg", width=300)
    
    st.header("📈 Sistema Plotter DIMOS - Full Control")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    
    # --- SIDEBAR: PULIZIA (LOGICA OTTIMO) ---
    st.sidebar.header("🛠️ Filtri e Pulizia")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri", value=True)
    use_gauss = st.sidebar.checkbox("Filtro Gauss (Sigma)", value=True)
    sigma_val = st.sidebar.slider("Sensibilità Gauss (Sigma)", 1.0, 5.0, 2.0, 0.1)
    use_rolling = st.sidebar.checkbox("Ammorbidimento (Media Mobile)", value=True)
    grado_poly = st.sidebar.selectbox("Trend Polinomiale", [0, 2, 3, 4], format_func=lambda x: "OFF" if x==0 else f"Grado {x}")

    # --- 1. MAPPATURA RIGIDA NOMI (DA FOGLIO 'NAME') ---
    anagrafica = {}
    if "NAME" in xls.sheet_names:
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        # Riga 0: Datalogger (C8A_202AS...), Riga 1: Sensore (CL_01...), Riga 2: Nome Web
        for c_idx in range(1, df_name.shape[1]):
            dl_name = str(df_name.iloc[0, c_idx]).strip()
            sens_name = str(df_name.iloc[1, c_idx]).strip()
            web_id = str(df_name.iloc[2, c_idx]).strip()
            
            if dl_name not in anagrafica: anagrafica[dl_name] = {}
            if sens_name not in anagrafica[dl_name]: anagrafica[dl_name][sens_name] = {"web_id": web_id, "cols": {}}
    else:
        st.error("ERRORE: Foglio 'NAME' non trovato. Impossibile mappare i sensori.")
        return

    # --- 2. CARICAMENTO DATI ---
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    # Popolamento colonne reali
    for dl in anagrafica:
        for sens in anagrafica[dl]:
            web_id = anagrafica[dl][sens]["web_id"]
            for col in df.columns:
                if web_id in col and "[" in col:
                    # Estrae la grandezza es. "X [°]"
                    grandezza = col.split(web_id)[-1].lstrip('_').strip()
                    if not grandezza: grandezza = re.search(r'\[.*?\]', col).group(0)
                    anagrafica[dl][sens]["cols"][grandezza] = col

    # --- 3. SELEZIONE MULTIPLA ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Intervallo Temporale", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    c1, c2, c3 = st.columns(3)
    with c1: sel_dls = st.multiselect("1. Datalogger", sorted(anagrafica.keys()))
    
    # Filtro Sensori
    list_s = []
    for d in sel_dls:
        for s in anagrafica[d].keys():
            list_s.append(f"{d} | {s}")
    with c2: sel_sens_f = st.multiselect("2. Sensori", list_s)
    
    # Filtro Grandezze
    list_g = set()
    for item in sel_sens_f:
        d, s = item.split(" | ")
        list_g.update(anagrafica[d][s]["cols"].keys())
    with c3: sel_grands = st.multiselect("3. Grandezze Fisiche", sorted(list(list_g)))

    # --- 4. FUNZIONE DI ELABORAZIONE (STESSA PER GRAFICO E STAMPA) ---
    def get_processed_data(col_name):
        y = df_f[col_name].copy()
        if clean_zeros: y = y.replace(0, np.nan)
        if use_gauss and y.notna().sum() > 5:
            m, s_dev = y.mean(), y.std()
            y = y.mask(abs(y - m) > (sigma_val * s_dev), np.nan)
        if use_rolling: y = y.rolling(window=5, center=True).mean()
        return y.interpolate(method='linear', limit_direction='both')

    # --- 5. GRAFICO ---
    fig = go.Figure()
    if sel_sens_f and sel_grands:
        for item in sel_sens_f:
            d, s = item.split(" | ")
            for g in sel_grands:
                if g in anagrafica[d][s]["cols"]:
                    real_col = anagrafica[d][s]["cols"][g]
                    y_plot = get_processed_data(real_col)
                    fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_plot, name=f"{s} ({d}) - {g}"))
                    
                    if grado_poly > 0:
                        x_n = np.arange(len(y_plot))
                        valid = y_plot.notna()
                        if valid.any():
                            p = np.poly1d(np.polyfit(x_n[valid], y_plot[valid], grado_poly))
                            fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=p(x_n), name=f"Trend {s} {g}", line=dict(dash='dot')))

        fig.update_layout(template="plotly_white", height=700, hovermode="x unified",
                          legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"))
        st.plotly_chart(fig, use_container_width=True)

        # --- 6. STAMPE (OPZIONALITÀ IDENTICA ALLA VISUALIZZAZIONE) ---
        st.divider()
        st.subheader("🖨️ Esportazione Report Word")
        tipo_stampa = st.radio("Cosa vuoi stampare?", ["Grafico Unico (Confronto)", "Un Grafico per ogni Sensore selezionato"])
        
        if st.button("🚀 GENERA DOCUMENTO"):
            if DOCX_AVAILABLE:
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO DIMOS', 0)
                doc.add_paragraph(f"Periodo: {sel_range[0]} - {sel_range[1]}")
                doc.add_paragraph(f"Filtri applicati: Gauss (Sigma {sigma_val}), Rimozione Zeri: {clean_zeros}")

                if tipo_stampa == "Grafico Unico (Confronto)":
                    img_io = BytesIO(pio.to_image(fig, format="png", width=1200, height=600))
                    doc.add_picture(img_io, width=Inches(6.3))
                else:
                    for item in sel_sens_f:
                        d, s = item.split(" | ")
                        doc.add_heading(f"Dettaglio Sensore: {s} ({d})", level=2)
                        f_tmp = go.Figure()
                        for g in sel_grands:
                            if g in anagrafica[d][s]["cols"]:
                                f_tmp.add_trace(go.Scatter(x=df_f['Data e Ora'], y=get_processed_data(anagrafica[d][s]["cols"][g]), name=g))
                        img_s = BytesIO(pio.to_image(f_tmp, format="png", width=1000, height=450))
                        doc.add_picture(img_s, width=Inches(6.0))
                        doc.add_page_break()

                buf = BytesIO(); doc.save(buf)
                st.download_button("📥 Scarica Report", buf.getvalue(), "Report_DIMOS.docx")
