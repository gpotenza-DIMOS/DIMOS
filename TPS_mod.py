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
    """Converte una serie in numerico gestendo virgole e spazi."""
    return pd.to_numeric(
        serie.astype(str).str.replace(",", ".", regex=False).str.replace(" ", "", regex=False),
        errors="coerce"
    )

def applica_filtro_sigma(serie, n_sigma=2.0):
    """Applica il filtro di Gauss (Sigma) per rimuovere gli outlier."""
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

def calcola_trend_polinomiale(x_dates, y_values, grado):
    """Calcola la curva di tendenza basata su regressione polinomiale."""
    try:
        # Convertiamo le date in formato numerico (timestamp) per la regressione
        x_numeric = np.array([d.timestamp() for d in x_dates])
        y_numeric = np.array(y_values)
        
        # Filtriamo eventuali NaN rimasti per il calcolo dei coefficienti
        mask = ~np.isnan(y_numeric)
        if mask.sum() <= grado: # Serve un numero di punti > del grado
            return None
            
        coeffs = np.polyfit(x_numeric[mask], y_numeric[mask], grado)
        poly_func = np.poly1d(coeffs)
        return poly_func(x_numeric)
    except Exception as e:
        logger.error(f"Errore calcolo trend: {e}")
        return None

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
def genera_report_word_separato(metodo, n_sigma, dati_report):
    doc = Document()
    doc.add_heading('DIMOS - REPORT ANALISI TOPOGRAFICA DETTAGLIATO', level=1)
    
    doc.add_paragraph(f"Metodo elaborazione: {metodo}")
    if metodo == "Filtro Sigma (Gauss)":
        doc.add_paragraph(f"Valore Sigma: {n_sigma}")

    for sezione in dati_report:
        doc.add_page_break() if dati_report.index(sezione) > 0 else None
        punto_nome = sezione['punto']
        doc.add_heading(f"Analisi Sensore: {punto_nome}", level=2)

        if sezione['img_path'] and os.path.exists(sezione['img_path']):
            doc.add_picture(sezione['img_path'], width=Inches(6.0))
        
        doc.add_heading(f"Metriche - {punto_nome}", level=3)
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        for i, text in enumerate(["Parametro", "MIN", "MAX", "RANGE", "ULTIMO"]):
            hdr_cells[i].text = text

        for m in sezione['metriche']:
            cells = table.add_row().cells
            cells[0].text = str(m["parametro"])
            cells[1].text = f"{m['min']:.3f}"
            cells[2].text = f"{m['max']:.3f}"
            cells[3].text = f"{m['range']:.3f}"
            cells[4].text = f"{m['ultimo']:.3f}"

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
        
        tutte_colonne = []
        for f in fogli:
            tutte_colonne.extend(estrai_colonne_numeriche(dfs[f]))
        colonne_uniche = sorted(list(set(tutte_colonne)))

        # --- 2. CONFIGURAZIONE VISUALIZZAZIONE ---
        st.subheader("📺 Configurazione Visualizzazione e Trend")
        c1, c2, c3 = st.columns([1.5, 1, 1])
        
        with c1:
            punti_video = st.multiselect("Seleziona Sensori", fogli, key="punti_video")
            parametri_video = st.multiselect("Parametri", colonne_uniche, 
                                           default=ottieni_default_params(colonne_uniche), key="params_video")

        with c2:
            metodo = st.radio("Metodo elaborazione", ["Dati Completi", "Filtro Sigma (Gauss)"], horizontal=False)
            n_sigma = 2.0
            if metodo == "Filtro Sigma (Gauss)":
                n_sigma = st.slider("Valore Sigma", 1.0, 5.0, 2.0, 0.5)

        with c3:
            st.markdown("**Trend Polinomiale**")
            attiva_trend = st.checkbox("Inserisci Curva di Tendenza", value=False)
            grado_trend = st.slider("Grado del Polinomio", 1, 5, 2) if attiva_trend else 1

        # --- 3. RENDERING VIDEO ---
        if punti_video and parametri_video:
            st.divider()
            fig_video = go.Figure()

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

                    if not d.empty:
                        # Dati reali
                        fig_video.add_trace(go.Scatter(x=d[col_data], y=d[parametro], 
                                                     mode="lines+markers", name=f"{punto}: {parametro}"))
                        # Calcolo e aggiunta Trend
                        if attiva_trend:
                            trend_vals = calcola_trend_polinomiale(d[col_data], d[parametro], grado_trend)
                            if trend_vals is not None:
                                fig_video.add_trace(go.Scatter(
                                    x=d[col_data], y=trend_vals, 
                                    mode="lines", 
                                    line=dict(dash='dash', width=2), 
                                    name=f"Trend {grado_trend}° ({punto})"))

            st.plotly_chart(fig_video, use_container_width=True)

            # --- 4. CONFIGURAZIONE WORD ---
            st.divider()
            st.subheader("📄 Configurazione Esportazione Report Word")
            w_col1, w_col2 = st.columns(2)
            with w_col1:
                punti_word_raw = st.multiselect("Layer per Word", ["TUTTI"] + fogli, default=punti_video, key="punti_word")
            with w_col2:
                parametri_word = st.multiselect("Parametri per layer", colonne_uniche, default=parametri_video, key="params_word")

            if st.button("🚀 Genera Report Word Dettagliato"):
                punti_effettivi = fogli if "TUTTI" in punti_word_raw else punti_word_raw
                if not punti_effettivi or not parametri_word:
                    st.warning("Seleziona sensori e parametri per il report.")
                else:
                    with st.spinner("Elaborazione grafici separati..."):
                        dati_per_report = []
                        for punto in punti_effettivi:
                            dfw = dfs[punto].copy()
                            col_dt = dfw.columns[0]
                            dfw[col_dt] = pd.to_datetime(dfw[col_dt], errors="coerce", dayfirst=True)
                            dfw = dfw.dropna(subset=[col_dt]).sort_values(col_dt)

                            fig_punto = go.Figure()
                            metriche_punto = []
                            
                            for param in parametri_word:
                                if param not in dfw.columns: continue
                                dw = dfw[[col_dt, param]].copy()
                                dw[param] = converti_numerico(dw[param])
                                dw = dw.dropna()
                                if metodo == "Filtro Sigma (Gauss)":
                                    dw[param] = applica_filtro_sigma(dw[param], n_sigma)
                                    dw = dw.dropna()
                                
                                if not dw.empty:
                                    metriche_punto.append({
                                        "parametro": param, "min": dw[param].min(), "max": dw[param].max(), 
                                        "range": dw[param].max() - dw[param].min(), "ultimo": dw[param].iloc[-1]
                                    })
                                    fig_punto.add_trace(go.Scatter(x=dw[col_dt], y=dw[param], mode="lines+markers", name=param))
                                    
                                    # Trend nel report
                                    if attiva_trend:
                                        t_vals = calcola_trend_polinomiale(dw[col_dt], dw[param], grado_trend)
                                        if t_vals is not None:
                                            fig_punto.add_trace(go.Scatter(x=dw[col_dt], y=t_vals, mode="lines", 
                                                                         line=dict(dash='dash', width=2), 
                                                                         name=f"Trend {grado_trend}°"))

                            if metriche_punto:
                                fig_punto.update_layout(title=f"Analisi {punto}", template="plotly_white")
                                img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                                fig_punto.write_image(img_tmp.name, width=1000, height=500)
                                dati_per_report.append({"punto": punto, "metriche": metriche_punto, "img_path": img_tmp.name})

                        if dati_per_report:
                            report_path = genera_report_word_separato(metodo, n_sigma, dati_per_report)
                            with open(report_path, "rb") as f:
                                st.download_button("⬇️ Scarica Report", f, "Report_DIMOS_Dettagliato.docx")
        else:
            st.info("Configura la visualizzazione per iniziare.")
    else:
        st.info("Carica un file Excel per procedere.")

if __name__ == "__main__":
    run_tps_monitoring()
