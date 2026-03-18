import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from docx import Document
from docx.shared import Inches

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(layout="wide", page_title="DIMOS Monitoraggio")

# --- HEADER: LOGO E TITOLO ---
# Logo largo 400px come richiesto
try:
    st.image("logo_dimos.jpg", width=400)
except:
    st.info("📌 [Inserire logo_dimos.jpg qui]")

st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
st.divider()

# --- SIDEBAR: SOLO FILTRI TECNICI ---
with st.sidebar:
    st.header("⚙️ Impostazioni Analisi")
    sigma_val = st.slider("Filtro Gauss (Soglia Sigma)", 0.0, 5.0, 3.0, 0.1)
    rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
    st.divider()
    st.info("I selettori di Datalogger e Sensori sono nella pagina principale.")

# --- FUNZIONI DI ELABORAZIONE ---
def applica_filtri(serie, n_sigma, drop_zeros):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    if drop_zeros:
        diag["zeri"] = int((originale == 0).sum())
        originale = originale.replace(0, np.nan)
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        mean, std = validi.mean(), validi.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diag["gauss"] = int(outliers.sum())
            originale[outliers] = np.nan
    return originale, diag

# --- PAGINA PRINCIPALE: CARICAMENTO ---
uploaded_file = st.file_uploader("📂 Carica file Excel (contenente fogli NAME e Dati) o CSV", type=['xlsx', 'csv'])

if uploaded_file:
    df_dati = pd.DataFrame()
    gerarchia = {}

    # 1. LETTURA DATI E GERARCHIA
    if uploaded_file.name.endswith('.xlsx'):
        xls = pd.ExcelFile(uploaded_file)
        # Cerchiamo il foglio NAME e il foglio dati (assumiamo il primo se non specificato)
        nome_foglio_dati = "flegrei" if "flegrei" in xls.sheet_names else xls.sheet_names[0]
        df_dati = pd.read_excel(xls, sheet_name=nome_foglio_dati)
        
        if "NAME" in xls.sheet_names:
            df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
            for i, col_name in enumerate(df_dati.columns):
                if i == 0: continue # Salta colonna tempo
                try:
                    dl = str(df_name.iloc[0, i]).strip()
                    sens = str(df_name.iloc[1, i]).strip()
                except:
                    dl, sens = "Generale", "Vari"
                if dl not in gerarchia: gerarchia[dl] = {}
                if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                gerarchia[dl][sens].append(col_name)
    else:
        # Fallback CSV o mancanza foglio NAME
        df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')

    # Se la gerarchia è vuota (manca foglio NAME), parsing dai nomi colonne
    if not gerarchia:
        for col in df_dati.columns[1:]:
            parts = col.split(' ')
            dl = parts[0].split('_')[0] + "_" + parts[0].split('_')[1] if '_' in parts[0] else parts[0]
            sens = parts[0]
            if dl not in gerarchia: gerarchia[dl] = {}
            if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
            gerarchia[dl][sens].append(col)

    # Identificazione colonna tempo
    col_t = df_dati.columns[0]
    df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
    df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)

    # 2. INTERFACCIA DI SELEZIONE (Pagina Principale)
    st.subheader("🔍 Selezione Dati")
    c1, c2 = st.columns(2)
    with c1:
        sel_dls = st.multiselect("Seleziona Centraline/Datalogger", options=sorted(list(gerarchia.keys())))
    with c2:
        opts_sens = []
        for d in sel_dls:
            opts_sens.extend(list(gerarchia[d].keys()))
        sel_sens = st.multiselect("Seleziona Sensori", options=sorted(list(set(opts_sens))))

    # Scelta Date
    st.write("**Intervallo Temporale**")
    min_d, max_d = df_dati[col_t].min(), df_dati[col_t].max()
    d1, d2 = st.columns(2)
    with d1: start_dt = st.date_input("Inizio", min_d)
    with d2: end_dt = st.date_input("Fine", max_d)

    # 3. GRAFICO E ANALISI
    colonne_finali = []
    for d in sel_dls:
        for s in sel_sens:
            if s in gerarchia[d]: colonne_finali.extend(gerarchia[d][s])

    if colonne_finali:
        mask = (df_dati[col_t].dt.date >= start_dt) & (df_dati[col_t].dt.date <= end_dt)
        df_p = df_dati.loc[mask]
        
        fig = go.Figure()
        stats = []

        for c in colonne_finali:
            y_p, info = applica_filtri(df_p[c], sigma_val, rimuovi_zeri)
            info["Parametro"] = c
            stats.append(info)
            fig.add_trace(go.Scatter(x=df_p[col_t], y=y_p, name=c, mode='lines'))

        # Grafico con cursori dinamici (Range Slider)
        fig.update_layout(
            height=600, template="plotly_white",
            xaxis=dict(rangeslider=dict(visible=True), type="date"),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Report Gauss e Zeri
        st.subheader("📊 Report Qualità (Analisi Gauss e Zeri)")
        st.table(pd.DataFrame(stats).set_index("Parametro"))

        # Download Ascisse TXT
        txt_ascisse = df_p[col_t].dt.strftime('%d/%m/%Y %H:%M:%S').to_string(index=False)
        st.download_button("💾 Scarica Ascisse (TXT)", txt_ascisse, "ascisse.txt")

        # Export Word
        if st.button("📄 Esporta Report Word"):
            doc = Document()
            doc.add_heading('DIMOS - Report Monitoraggio', 0)
            doc.add_paragraph(f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            doc.add_paragraph(f"Filtro Gauss (Sigma): {sigma_val} | Rimozione Zeri: {rimuovi_zeri}")
            # Tabella riassuntiva
            t = doc.add_table(rows=1, cols=3)
            t.rows[0].cells[0].text = 'Parametro'
            t.rows[0].cells[1].text = 'Zeri Rimossi'
            t.rows[0].cells[2].text = 'Outliers (Gauss)'
            for s in stats:
                row = t.add_row().cells
                row[0].text, row[1].text, row[2].text = str(s['Parametro']), str(s['zeri']), str(s['gauss'])
            
            buf = BytesIO()
            doc.save(buf)
            st.download_button("Scarica Word", buf.getvalue(), "Report_Dimos.docx")
    else:
        st.info("Seleziona almeno una centralina e un sensore per generare il grafico.")
