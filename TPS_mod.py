import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
import logging
import tempfile
import os

from docx import Document
from docx.shared import Inches

# =========================================================
# CONFIGURAZIONE E UTILITY
# =========================================================
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DIMOS")

def converti_numerico(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace(",", ".", regex=False).str.replace(" ", "", regex=False),
        errors="coerce"
    )

def applica_filtro_sigma(serie, n_sigma=2.0):
    try:
        serie = converti_numerico(serie)
        media = serie.mean()
        std = serie.std()
        if pd.isna(std) or std == 0:
            return serie
        filtro = ((serie >= media - n_sigma * std) & (serie <= media + n_sigma * std))
        return serie.where(filtro)
    except Exception as e:
        logger.error(f"Errore filtro sigma: {e}")
        return serie

@st.cache_data
def carica_excel(uploaded_file):
    data = {}
    try:
        xl = pd.ExcelFile(uploaded_file, engine="openpyxl")
        for sheet in xl.sheet_names:
            df = xl.parse(sheet, header=0)
            df = df.dropna(how="all")
            df.columns = [str(c).strip() for c in df.columns]
            data[sheet] = df
        return data
    except Exception as e:
        logger.error(f"Errore caricamento Excel: {e}")
        return {}

def estrai_colonne_numeriche(df):
    colonne = []
    for c in df.columns[1:]:
        if "Unnamed" in str(c): continue
        serie_test = converti_numerico(df[c])
        if serie_test.notnull().sum() > 0:
            colonne.append(c)
    return colonne

# =========================================================
# CREAZIONE REPORT WORD
# =========================================================
def genera_report_word(punti, configurazione, metodo, n_sigma, metriche_globali, image_path):
    doc = Document()
    doc.add_heading('DIMOS - REPORT ANALISI TOPOGRAFICA', level=1)
    
    doc.add_paragraph(f"Metodo elaborazione: {metodo}")
    if metodo == "Filtro Sigma (Gauss)":
        doc.add_paragraph(f"Valore Sigma: {n_sigma}")

    # Sezione Grafico
    if image_path and os.path.exists(image_path):
        doc.add_heading('Visualizzazione Dati', level=2)
        doc.add_picture(image_path, width=Inches(6.5))

    # Sezione Metriche
    doc.add_heading('Tabella Metriche', level=2)
    table = doc.add_table(rows=1, cols=6)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, text in enumerate(["Punto", "Parametro", "MIN", "MAX", "RANGE", "ULTIMO"]):
        hdr_cells[i].text = text

    for row in metriche_globali:
        cells = table.add_row().cells
        cells[0].text = str(row["punto"])
        cells[1].text = str(row["parametro"])
        cells[2].text = f"{row['min']:.3f}"
        cells[3].text = f"{row['max']:.3f}"
        cells[4].text = f"{row['range']:.3f}"
        cells[5].text = f"{row['ultimo']:.3f}"

    tmp_docx = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(tmp_docx.name)
    return tmp_docx.name

# =========================================================
# APP PRINCIPALE
# =========================================================
def run_tps_monitoring():
    st.set_page_config(page_title="DIMOS - Analisi Topografica", layout="wide")
    
    st.title("🛰️ DIMOS - Analisi Topografica Avanzata")
    
    # --- 1. CARICAMENTO FILE ---
    with st.container(border=True):
        uploaded_file = st.file_uploader("📂 Carica file Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        dfs = carica_excel(uploaded_file)
        fogli = list(dfs.keys())
        
        # --- 2. CONFIGURAZIONE NELLA PAGINA PRINCIPALE ---
        st.subheader("⚙️ Configurazione Analisi")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            punti_selezionati = st.multiselect(
                "Seleziona Sensori/Punti (Layer)", 
                fogli, 
                help="Scegli uno o più fogli da analizzare"
            )
        with c2:
            metodo = st.radio("Metodo elaborazione", ["Dati Completi", "Filtro Sigma (Gauss)"], horizontal=True)
            n_sigma = 2.0
            if metodo == "Filtro Sigma (Gauss)":
                n_sigma = st.slider("Valore Sigma", 1.0, 5.0, 2.0, 0.5)

        if not punti_selezionati:
            st.info("Seleziona almeno un sensore per iniziare l'analisi.")
            return

        # Scelta parametri per ogni sensore
        configurazione = {}
        st.markdown("#### 🔍 Selezione Parametri per Sensore")
        
        # Usiamo le colonne per non allungare troppo la pagina se ci sono molti sensori
        cols_punti = st.columns(len(punti_selezionati))
        for i, punto in enumerate(punti_selezionati):
            with cols_punti[i]:
                df_temp = dfs[punto]
                colonne_disp = estrai_colonne_numeriche(df_temp)
                selezione = st.multiselect(
                    f"Parametri {punto}", 
                    colonne_disp, 
                    default=colonne_disp[:1],
                    key=f"params_{punto}"
                )
                configurazione[punto] = selezione

        # --- 3. ELABORAZIONE E GRAFICI ---
        st.divider()
        fig = go.Figure()
        metriche_globali = []

        for punto in configurazione:
            if not configurazione[punto]: continue
            
            df = dfs[punto].copy()
            col_data = df.columns[0] # Assumiamo la prima colonna sia la data
            df[col_data] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)
            df = df.dropna(subset=[col_data]).sort_values(col_data)

            for parametro in configurazione[punto]:
                d = df[[col_data, parametro]].copy()
                d[parametro] = converti_numerico(d[parametro])
                d = d.dropna()

                if metodo == "Filtro Sigma (Gauss)":
                    d[parametro] = applica_filtro_sigma(d[parametro], n_sigma)
                    d = d.dropna()

                if d.empty: continue

                # Calcolo Metriche
                minimo, massimo = d[parametro].min(), d[parametro].max()
                ultimo = d[parametro].iloc[-1]
                metriche_globali.append({
                    "punto": punto, "parametro": parametro,
                    "min": minimo, "max": massimo, "range": massimo - minimo, "ultimo": ultimo
                })

                # Aggiunta al Grafico
                fig.add_trace(go.Scatter(
                    x=d[col_data], y=d[parametro],
                    mode="lines+markers", name=f"{punto}: {parametro}"
                ))

        # Visualizzazione Metriche
        if metriche_globali:
            st.subheader("📊 Metriche Real-time")
            m_cols = st.columns(4)
            for idx, m in enumerate(metriche_globali):
                m_cols[idx % 4].metric(
                    label=f"{m['punto']} | {m['parametro']}",
                    value=f"{m['ultimo']:.3f}",
                    delta=f"R: {m['range']:.3f}",
                    delta_color="normal"
                )

            # Visualizzazione Grafico
            fig.update_layout(
                template="plotly_white", height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(title="Data", tickformat="%d/%m/%Y"),
                yaxis=dict(title="Valore Numerico")
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- 4. ESPORTAZIONE ---
            st.divider()
            col_exp, col_empty = st.columns([1, 2])
            
            with col_exp:
                st.subheader("📄 Esportazione Report")
                if st.button("🚀 Genera Report Word con Grafico Corrente"):
                    with st.spinner("Generazione in corso..."):
                        # Salvataggio temporaneo immagine per Word
                        img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        try:
                            fig.write_image(img_tmp.name, width=1200, height=600)
                            
                            report_path = genera_report_word(
                                punti=punti_selezionati,
                                configurazione=configurazione,
                                metodo=metodo,
                                n_sigma=n_sigma,
                                metriche_globali=metriche_globali,
                                image_path=img_tmp.name
                            )

                            with open(report_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Scarica Report Word",
                                    data=f,
                                    file_name=f"Report_DIMOS_{punto}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )
                        except Exception as e:
                            st.error(f"Errore durante l'esportazione: {e}. Assicurati di avere 'kaleido' installato.")

    else:
        st.info("Benvenuto in DIMOS. Carica un file Excel per iniziare l'analisi topografica.")

if __name__ == "__main__":
    run_tps_monitoring()
