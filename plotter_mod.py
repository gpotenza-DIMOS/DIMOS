import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from docx import Document
from docx.shared import Inches

def applica_filtri_statistici(serie, n_sigma, rimuovi_zeri):
    """Esegue la pulizia dei dati: rimozione zeri e filtro Gaussiano."""
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    
    if rimuovi_zeri:
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

def main():
    # --- CONFIGURAZIONE LOGO E TITOLO ---
    col_logo, col_titolo = st.columns([1, 4])
    with col_logo:
        try:
            st.image("logo_dimos.jpg", width=150)
        except:
            st.info("Logo DIMOS")
    
    with col_titolo:
        st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
    
    st.divider()

    # --- SIDEBAR: IMPOSTAZIONI ANALISI E FILTRI ---
    with st.sidebar:
        st.header("⚙️ Impostazioni Analisi")
        
        uploaded_data = st.file_uploader("1. Carica File Dati (CSV/XLSX)", type=['csv', 'xlsx'])
        uploaded_name = st.file_uploader("2. Carica File NAME (Opzionale)", type=['csv', 'xlsx'])
        
        st.divider()
        st.subheader("Filtri Statistici")
        rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
        sigma = st.slider("Filtro Gauss (Soglia Sigma)", 0.0, 5.0, 3.0, 0.1)
        
        st.divider()
        st.subheader("Esportazione Ausiliaria")
        esporta_txt = st.button("Genera Elenco Ascisse (TXT)")

    if uploaded_data:
        # Caricamento dati
        if uploaded_data.name.endswith('.csv'):
            df = pd.read_csv(uploaded_data, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_data)
        
        # Identificazione automatica colonna temporale
        col_tempo = df.columns[0]
        for c in df.columns:
            if 'data' in c.lower() or 'ora' in c.lower():
                col_tempo = c
                break
        
        df[col_tempo] = pd.to_datetime(df[col_tempo], dayfirst=True, errors='coerce')
        df = df.dropna(subset=[col_tempo]).sort_values(col_tempo)

        # --- COSTRUZIONE GERARCHIA (Centralina -> Sensore -> Parametri) ---
        gerarchia = {}
        
        if uploaded_name:
            # Lettura layer NAME (Riga 1: DL, Riga 2: Sensore, Riga 3: Nome Web)
            if uploaded_name.name.endswith('.csv'):
                df_n = pd.read_csv(uploaded_name, header=None, sep=None, engine='python')
            else:
                df_n = pd.read_excel(uploaded_name, header=None)
                
            for i, col_name in enumerate(df.columns):
                if col_name == col_tempo: continue
                try:
                    dl = str(df_n.iloc[0, i]).strip()
                    sens = str(df_n.iloc[1, i]).strip()
                except:
                    dl, sens = "Generale", "Vari"
                
                if dl not in gerarchia: gerarchia[dl] = {}
                if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                gerarchia[dl][sens].append(col_name)
        else:
            # Fallback: Parsing dei nomi colonne (es: CO_9286 BATT [V])
            for col in df.columns:
                if col == col_tempo: continue
                parts = col.split(' ')
                dl = parts[0].split('_')[0] + "_" + parts[0].split('_')[1] if '_' in parts[0] else parts[0]
                sens = parts[0] # Identificativo sensore
                
                if dl not in gerarchia: gerarchia[dl] = {}
                if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                gerarchia[dl][sens].append(col)

        # --- SELEZIONE DATI NELLA PAGINA PRINCIPALE ---
        st.subheader("🔍 Selezione Centraline e Sensori")
        c1, c2 = st.columns(2)
        
        with c1:
            sel_dl = st.multiselect("Seleziona Datalogger", options=sorted(list(gerarchia.keys())))
        
        with c2:
            sens_opts = []
            for d in sel_dl:
                sens_opts.extend(list(gerarchia[d].keys()))
            sel_sens = st.multiselect("Seleziona Sensori", options=sorted(list(set(sens_opts))))

        # Selezione Temporale con cursori e manuale
        st.write("---")
        st.subheader("📅 Definizione Intervallo Temporale")
        min_date, max_date = df[col_tempo].min(), df[col_tempo].max()
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_dt = st.date_input("Inizio", min_date, min_value=min_date, max_value=max_date)
        with col_t2:
            end_dt = st.date_input("Fine", max_date, min_value=min_date, max_value=max_date)

        # --- ELABORAZIONE E GRAFICO ---
        colonne_finali = []
        for d in sel_dl:
            for s in sel_sens:
                if s in gerarchia[d]:
                    colonne_finali.extend(gerarchia[d][s])

        if colonne_finali:
            mask = (df[col_tempo].dt.date >= start_dt) & (df[col_tempo].dt.date <= end_dt)
            df_p = df.loc[mask]
            
            fig = go.Figure()
            report_stats = []

            for col in colonne_finali:
                y_pulita, diag = applica_filtri_statistici(df_p[col], sigma, rimuovi_zeri)
                diag["Parametro"] = col
                report_stats.append(diag)
                
                fig.add_trace(go.Scatter(
                    x=df_p[col_tempo], y=y_pulita, name=col,
                    mode='lines+markers', marker=dict(size=4),
                    connectgaps=False
                ))

            fig.update_layout(
                height=600,
                template="plotly_white",
                xaxis=dict(rangeslider=dict(visible=True), type="date"),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Report Gauss e Zeri
            st.subheader("📊 Report Qualità Dati")
            st.table(pd.DataFrame(report_stats).set_index("Parametro"))

            # Export Word
            if st.button("📄 Esporta Report Word"):
                doc = Document()
                doc.add_heading('Monitoraggio Strutturale - DIMOS', 0)
                doc.add_paragraph(f"Periodo analisi: {start_dt} - {end_dt}")
                doc.add_paragraph(f"Filtri: Sigma={sigma}, Rimozione Zeri={rimuovi_zeri}")
                
                table = doc.add_table(rows=1, cols=3)
                hdr = table.rows[0].cells
                hdr[0].text, hdr[1].text, hdr[2].text = 'Parametro', 'Zeri Rimossi', 'Outlier Gauss'
                for r in report_stats:
                    row = table.add_row().cells
                    row[0].text, row[1].text, row[2].text = str(r['Parametro']), str(r['zeri_rimossi']), str(r['outliers_gauss'])
                
                buffer = BytesIO()
                doc.save(buffer)
                st.download_button("Scarica Report Word", buffer.getvalue(), "Report_DIMOS.docx")

        if esporta_txt:
            ascisse = df[col_tempo].dt.strftime('%Y-%m-%d %H:%M:%S').to_string(index=False)
            st.download_button("Scarica Ascisse (TXT)", ascisse, "ascisse.txt")

    else:
        st.info("Carica i file nella barra laterale per iniziare l'analisi.")

if __name__ == "__main__":
    main()
