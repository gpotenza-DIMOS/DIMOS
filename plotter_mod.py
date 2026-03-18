import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from docx import Document

def applica_filtri(serie, sigma, rimuovi_zeri):
    info = {'zeri_rimossi': 0, 'outliers_gauss': 0}
    clean_serie = serie.copy()
    if rimuovi_zeri:
        info['zeri_rimossi'] = int((clean_serie == 0).sum())
        clean_serie = clean_serie.replace(0, np.nan)
    if sigma > 0:
        mean = clean_serie.mean()
        std = clean_serie.std()
        outliers = (clean_serie < mean - sigma * std) | (clean_serie > mean + sigma * std)
        info['outliers_gauss'] = int(outliers.sum())
        clean_serie[outliers] = np.nan
    return clean_serie, info

def main():
    # --- HEADER ---
    col_logo, col_titolo = st.columns([1, 4])
    with col_logo:
        try:
            st.image("logo_dimos.jpg", width=150)
        except:
            st.write("📌 Logo DIMOS")
    with col_titolo:
        st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")

    # --- SIDEBAR (FILTRI E CARICAMENTO) ---
    with st.sidebar:
        st.header("⚙️ Impostazioni Analisi")
        file_dati = st.file_uploader("Carica File Dati (CSV/XLSX)", type=['csv', 'xlsx'])
        file_name = st.file_uploader("Carica File NAME (Opzionale)", type=['csv'])
        st.divider()
        sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0, 0.1)
        no_zeros = st.checkbox("Elimina valori '0'", value=True)

    if file_dati:
        df = pd.read_csv(file_dati, sep=None, engine='python')
        col_data = df.columns[0] # Assumiamo la prima colonna sia il tempo
        df[col_data] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        df = df.dropna(subset=[col_data]).sort_values(col_data)

        # Costruzione gerarchia Centralina -> Sensore
        gerarchia = {}
        if file_name:
            df_n = pd.read_csv(file_name, header=None, sep=None, engine='python')
            for i, col_name in enumerate(df.columns):
                if col_name == col_data: continue
                try:
                    cent = str(df_n.iloc[0, i]).strip()
                    sens = str(df_n.iloc[1, i]).strip()
                except:
                    cent, sens = "Generale", "Vari"
                if cent not in gerarchia: gerarchia[cent] = {}
                if sens not in gerarchia[cent]: gerarchia[cent][sens] = []
                gerarchia[cent][sens].append(col_name)
        else:
            # Fallback automatico se manca il file NAME
            for col in df.columns:
                if col == col_data: continue
                parts = col.split(' ')
                cent = parts[0].split('_')[0] + "_" + parts[0].split('_')[1] if '_' in parts[0] else "Centralina"
                sens = parts[0]
                if cent not in gerarchia: gerarchia[cent] = {}
                if sens not in gerarchia[cent]: gerarchia[cent][sens] = []
                gerarchia[cent][sens].append(col)

        # --- SELEZIONE UI ---
        st.subheader("🔍 Selezione Sensori")
        c1, c2 = st.columns(2)
        with c1:
            sel_cent = st.multiselect("Centraline", options=sorted(list(gerarchia.keys())))
        with c2:
            sens_disponibili = []
            for c in sel_cent: sens_disponibili.extend(list(gerarchia[c].keys()))
            sel_sens = st.multiselect("Sensori", options=sorted(list(set(sens_disponibili))))

        # Selezione Temporale
        min_d, max_d = df[col_data].min().date(), df[col_data].max().date()
        st.write("**Selezione Periodo (Inizio - Fine)**")
        t1, t2 = st.columns(2)
        with t1: start_date = st.date_input("Data Inizio", min_d)
        with t2: end_date = st.date_input("Data Fine", max_d)

        # --- GRAFICO E REPORT ---
        colonne_finali = []
        for c in sel_cent:
            for s in sel_sens:
                if s in gerarchia[c]: colonne_finali.extend(gerarchia[c][s])

        if colonne_finali:
            mask = (df[col_data].dt.date >= start_date) & (df[col_data].dt.date <= end_date)
            df_plot = df.loc[mask]
            
            fig = go.Figure()
            report_data = []

            for col in colonne_finali:
                y_clean, info = applica_filtri(df_plot[col], sigma_val, no_zeros)
                info['Parametro'] = col
                report_data.append(info)
                fig.add_trace(go.Scatter(x=df_plot[col_data], y=y_clean, name=col))

            fig.update_layout(xaxis=dict(rangeslider=dict(visible=True)), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # Tabella Gauss e Zeri
            st.subheader("📋 Report Qualità")
            st.table(pd.DataFrame(report_data).set_index('Parametro'))

            # Export Word
            if st.button("📄 Genera Report Word"):
                doc = Document()
                doc.add_heading('Dati Monitoraggio - DIMOS', 0)
                doc.add_paragraph(f"Periodo: {start_date} a {end_date}")
                # Aggiungi qui la logica tabelle/testo per Word
                buf = BytesIO()
                doc.save(buf)
                st.download_button("Scarica Word", buf.getvalue(), "Report.docx")
    else:
        st.info("Carica i file nella barra laterale per visualizzare i dati.")

# Essenziale per far funzionare il richiamo dal pulsante
if __name__ == "__main__":
    main()
