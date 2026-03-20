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
    
    st.header("📈 Plotter Professionale DIMOS - Selezione Granulare")

    file_input = st.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="p_up")
    if not file_input: return

    xls = pd.ExcelFile(file_input)
    
    # --- 1. MAPPATURA SECONDO LE TUE RIGHE ---
    anagrafica = {} # { Datalogger: { Sensore: { "Etichetta": "Nome_Colonna_Reale" } } }
    
    if "NAME" in xls.sheet_names:
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        # Riga 0 (A1, B1...): Datalogger
        # Riga 1 (A2, B2...): Sensore
        # Riga 2 (A3, B3...): Nome Web Completo (es: CO_9277 CL_01_X [°])
        
        for c_idx in range(1, df_name.shape[1]):
            dl = str(df_name.iloc[0, c_idx]).strip()
            sens = str(df_name.iloc[1, c_idx]).strip()
            full_web_name = str(df_name.iloc[2, c_idx]).strip()
            
            if dl == "nan" or full_web_name == "nan": continue

            if dl not in anagrafica: anagrafica[dl] = {}
            if sens not in anagrafica[dl]: anagrafica[dl][sens] = {}
            
            # Estraiamo la grandezza (quello che c'è dopo il nome web o l'unita di misura)
            # Per SD_301 avremo diverse voci qui
            grandezza = full_web_name
            if "_" in full_web_name:
                parts = full_web_name.split("_")
                grandezza = parts[-1] # Prende l'ultima parte es. "X [°]" o "LM [m]"
            
            anagrafica[dl][sens][grandezza] = full_web_name
    else:
        st.warning("Layer 'NAME' non trovato. Caricamento nomi web standard...")
        # Gestione fallback se NAME manca (come da tua richiesta)

    # --- 2. CARICAMENTO DATI ---
    sheets_dati = [s for s in xls.sheet_names if s not in ["NAME", "ARRAY", "Info"]]
    sel_sheet = st.selectbox("Seleziona Layer Dati", sheets_dati)
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    df.columns = [str(c).strip() for c in df.columns]
    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])

    # --- 3. FILTRI SIDEBAR ---
    st.sidebar.header("⚙️ Pulizia Dati")
    clean_zeros = st.sidebar.checkbox("Rimuovi Zeri", value=True)
    use_gauss = st.sidebar.checkbox("Filtro Gaussiano", value=True)
    sigma_val = st.sidebar.slider("Sigma", 1.0, 5.0, 2.0, 0.1)

    # --- 4. SELEZIONE GRANULARE (3 LIVELLI) ---
    st.divider()
    t_min, t_max = df['Data e Ora'].min().to_pydatetime(), df['Data e Ora'].max().to_pydatetime()
    sel_range = st.slider("Intervallo Temporale", t_min, t_max, (t_min, t_max))
    df_f = df[(df['Data e Ora'] >= sel_range[0]) & (df['Data e Ora'] <= sel_range[1])].copy()

    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_dls = st.multiselect("1. Seleziona Datalogger", sorted(anagrafica.keys()))
    
    with col2:
        # Mostra i sensori univoci per i DL selezionati
        sens_options = []
        for dl in selected_dls:
            for s in anagrafica[dl].keys():
                if f"{dl} | {s}" not in sens_options:
                    sens_options.append(f"{dl} | {s}")
        selected_sens_pairs = st.multiselect("2. Seleziona Sensore", sens_options)
    
    with col3:
        # Qui esplodono le grandezze fisiche (X, Y, Z, T1...)
        grand_options = set()
        for pair in selected_sens_pairs:
            dl_p, sens_p = pair.split(" | ")
            grand_options.update(anagrafica[dl_p][sens_p].keys())
        selected_grands = st.multiselect("3. Seleziona Grandezze Fisiche", sorted(list(grand_options)))

    # --- 5. FUNZIONE DI ELABORAZIONE ---
    def process(col):
        y = df_f[col].copy()
        if clean_zeros: y = y.replace(0, np.nan)
        if use_gauss and y.notna().sum() > 5:
            m, s = y.mean(), y.std()
            y = y.mask(abs(y - m) > (sigma_val * s), np.nan)
        return y.interpolate(limit_direction='both')

    # --- 6. GRAFICO ---
    fig = go.Figure()
    if selected_sens_pairs and selected_grands:
        for pair in selected_sens_pairs:
            dl_p, sens_p = pair.split(" | ")
            for g in selected_grands:
                if g in anagrafica[dl_p][sens_p]:
                    full_col = anagrafica[dl_p][sens_p][g]
                    if full_col in df.columns:
                        y_vals = process(full_col)
                        fig.add_trace(go.Scatter(x=df_f['Data e Ora'], y=y_vals, name=f"{sens_p} - {g}"))

        fig.update_layout(template="plotly_white", height=700, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # --- 7. STAMPE (PRODUZIONE SPECULARE) ---
        st.divider()
        st.subheader("💾 Produzione File di Stampa")
        cw, ce = st.columns(2)

        with cw:
            if st.button("📝 GENERA REPORT WORD"):
                doc = Document()
                doc.add_heading('REPORT MONITORAGGIO - DIMOS', 0)
                doc.add_paragraph(f"Visualizzazione di: {', '.join(selected_grands)}")
                # Inserisce lo STESSO grafico visto sopra
                img_io = BytesIO(pio.to_image(fig, format="png", width=1000, height=500))
                doc.add_picture(img_io, width=Inches(6.2))
                
                buf_w = BytesIO(); doc.save(buf_w)
                st.download_button("📥 Scarica Word", buf_w.getvalue(), "Report.docx")

        with ce:
            if st.button("📊 GENERA EXCEL STAMPA"):
                # Excel con i dati filtrati e selezionati a video
                df_out = pd.DataFrame({'Data Ora': df_f['Data e Ora']})
                for pair in selected_sens_pairs:
                    dl_p, sens_p = pair.split(" | ")
                    for g in selected_grands:
                        if g in anagrafica[dl_p][sens_p]:
                            fc = anagrafica[dl_p][sens_p][g]
                            df_out[f"{sens_p}_{g}"] = process(fc)
                
                buf_e = BytesIO()
                df_out.to_excel(buf_e, index=False)
                st.download_button("📥 Scarica Excel", buf_e.getvalue(), "Dati_Stampa.xlsx")
