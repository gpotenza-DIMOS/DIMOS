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

def ottieni_default_params(lista_colonne):
    """Ritorna DeltaE e DeltaN se presenti, altrimenti le prime disponibili."""
    defaults = [c for c in lista_colonne if c.upper() in ["DELTAE", "DELTAN", "DELTA E", "DELTA N"]]
    if not defaults and len(lista_colonne) > 0:
        return [lista_colonne[0]]
    return defaults

# =========================================================
# CREAZIONE REPORT WORD
# =========================================================
def genera_report_word(metodo, n_sigma, metriche_globali, image_path):
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
    
    with st.container(border=True):
        uploaded_file = st.file_uploader("📂 Carica file Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        dfs = carica_excel(uploaded_file)
        fogli = list(dfs.keys())
        
        # Estraiamo tutte le colonne numeriche possibili da tutti i fogli per i menu di scelta
        tutte_colonne = []
        for f in fogli:
            tutte_colonne.extend(estrai_colonne_numeriche(dfs[f]))
        colonne_uniche = sorted(list(set(tutte_colonne)))

        # --- 2. CONFIGURAZIONE VISUALIZZAZIONE ---
        st.subheader("📺 Configurazione Visualizzazione (Grafico)")
        c1, c2 = st.columns([2, 1])
        
        with c1:
            punti_video = st.multiselect(
                "Seleziona Sensori/Punti da visualizzare", 
                fogli, 
                key="punti_video"
            )
            
            # Se ci sono punti selezionati, mostro la scelta parametri unificata
            parametri_video = []
            if punti_video:
                parametri_video = st.multiselect(
                    "Parametri da graficare (saranno applicati a tutti i sensori selezionati)",
                    colonne_uniche,
                    default=ottieni_default_params(colonne_uniche),
                    key="params_video"
                )

        with c2:
            metodo = st.radio("Metodo elaborazione", ["Dati Completi", "Filtro Sigma (Gauss)"], horizontal=True)
            n_sigma = 2.0
            if metodo == "Filtro Sigma (Gauss)":
                n_sigma = st.slider("Valore Sigma", 1.0, 5.0, 2.0, 0.5)

        # --- 3. ELABORAZIONE E RENDERING GRAFICO VIDEO ---
        if punti_video and parametri_video:
            st.divider()
            fig = go.Figure()
            metriche_video = []

            for punto in punti_video:
                df = dfs[punto].copy()
                col_data = df.columns[0]
                df[col_data] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)
                df = df.dropna(subset=[col_data]).sort_values(col_data)

                for parametro in parametri_video:
                    if parametro not in df.columns: continue
                    
                    d = df[[col_data, parametro]].copy()
                    d[parametro] = converti_numerico(d[parametro])
                    d = d.dropna()

                    if metodo == "Filtro Sigma (Gauss)":
                        d[parametro] = applica_filtro_sigma(d[parametro], n_sigma)
                        d = d.dropna()

                    if d.empty: continue

                    # Calcolo Metriche per Video
                    minimo, massimo = d[parametro].min(), d[parametro].max()
                    ultimo = d[parametro].iloc[-1]
                    metriche_video.append({
                        "punto": punto, "parametro": parametro,
                        "min": minimo, "max": massimo, "range": massimo - minimo, "ultimo": ultimo
                    })

                    fig.add_trace(go.Scatter(
                        x=d[col_data], y=d[parametro],
                        mode="lines+markers", name=f"{punto}: {parametro}"
                    ))

            # Visualizzazione Metriche Video
            st.subheader("📊 Metriche Real-time (Video)")
            m_cols = st.columns(4)
            for idx, m in enumerate(metriche_video):
                m_cols[idx % 4].metric(
                    label=f"{m['punto']} | {m['parametro']}",
                    value=f"{m['ultimo']:.3f}",
                    delta=f"R: {m['range']:.3f}"
                )

            fig.update_layout(
                template="plotly_white", height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(title="Data", tickformat="%d/%m/%Y"),
                yaxis=dict(title="Valore Numerico")
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- 4. CONFIGURAZIONE SEPARATA PER WORD ---
            st.divider()
            st.subheader("📄 Configurazione Esportazione Report Word")
            
            w_col1, w_col2 = st.columns(2)
            with w_col1:
                opzioni_sensori_word = ["TUTTI"] + fogli
                punti_word_raw = st.multiselect(
                    "Seleziona Sensori per il file Word",
                    opzioni_sensori_word,
                    default=punti_video, # Propone quelli a video come punto di partenza
                    key="punti_word"
                )
            with w_col2:
                parametri_word = st.multiselect(
                    "Seleziona Parametri per il file Word",
                    colonne_uniche,
                    default=parametri_video if parametri_video else ottieni_default_params(colonne_uniche),
                    key="params_word"
                )

            if st.button("🚀 Genera Report Word con Impostazioni di Stampa"):
                # Logica per gestire l'opzione "TUTTI"
                if "TUTTI" in punti_word_raw:
                    punti_effettivi_word = fogli
                else:
                    punti_effettivi_word = punti_word_raw

                if not punti_effettivi_word or not parametri_word:
                    st.warning("Seleziona almeno un sensore e un parametro per il Word.")
                else:
                    with st.spinner("Generazione Report Word in corso..."):
                        # Generiamo un grafico ad hoc per il Word in base alla selezione separata
                        fig_word = go.Figure()
                        metriche_word = []

                        for punto in punti_effettivi_word:
                            dfw = dfs[punto].copy()
                            col_data_w = dfw.columns[0]
                            dfw[col_data_w] = pd.to_datetime(dfw[col_data_w], errors="coerce", dayfirst=True)
                            dfw = dfw.dropna(subset=[col_data_w]).sort_values(col_data_w)

                            for parametro_w in parametri_word:
                                if parametro_w not in dfw.columns: continue
                                dw = dfw[[col_data_w, parametro_w]].copy()
                                dw[parametro_w] = converti_numerico(dw[parametro_w])
                                dw = dw.dropna()

                                if metodo == "Filtro Sigma (Gauss)":
                                    dw[parametro_w] = applica_filtro_sigma(dw[parametro_w], n_sigma)
                                    dw = dw.dropna()

                                if dw.empty: continue

                                metriche_word.append({
                                    "punto": punto, "parametro": parametro_w,
                                    "min": dw[parametro_w].min(), "max": dw[parametro_w].max(), 
                                    "range": dw[parametro_w].max() - dw[parametro_w].min(), "ultimo": dw[parametro_w].iloc[-1]
                                })
                                fig_word.add_trace(go.Scatter(x=dw[col_data_w], y=dw[parametro_w], mode="lines+markers", name=f"{punto}: {parametro_w}"))

                        fig_word.update_layout(template="plotly_white", width=1200, height=600)
                        
                        img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        try:
                            fig_word.write_image(img_tmp.name)
                            report_path = genera_report_word(metodo, n_sigma, metriche_word, img_tmp.name)

                            with open(report_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Scarica Report Word",
                                    data=f,
                                    file_name="Report_Analisi_DIMOS.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )
                        except Exception as e:
                            st.error(f"Errore esportazione: {e}. Assicurati di avere 'kaleido' installato.")
        else:
            st.info("Seleziona almeno un sensore e un parametro per visualizzare l'analisi.")

    else:
        st.info("Benvenuto in DIMOS. Carica un file Excel per iniziare l'analisi topografica.")

if __name__ == "__main__":
    run_tps_monitoring()
