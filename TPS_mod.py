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

# Dizionario per la traduzione dei mesi in italiano per Plotly
MONTHS_IT = {
    "Jan": "Gen", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr", "May": "Mag", "Jun": "Giu",
    "Jul": "Lug", "Aug": "Ago", "Sep": "Set", "Oct": "Ott", "Nov": "Nov", "Dec": "Dic"
}

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

def calcola_trend_polinomiale(x_dates, y_values, grado):
    try:
        x_numeric = np.array([d.timestamp() for d in x_dates])
        y_numeric = np.array(y_values)
        mask = ~np.isnan(y_numeric)
        if mask.sum() <= grado:
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
    defaults = [c for c in lista_colonne if c.upper() in ["DELTAE", "DELTAN"]]
    if not defaults and len(lista_colonne) > 0:
        return [lista_colonne[0]]
    return defaults

# =========================================================
# CREAZIONE REPORT WORD
# =========================================================
def genera_report_word_separato(metodo, n_sigma, dati_report):
    doc = Document()
    doc.add_heading('DIMOS - REPORT ANALISI MONITORAGGIO TOPOGRAFICO ', level=1)
    doc.add_paragraph(f"Metodo elaborazione dati Word: {metodo}")
    if "Sigma" in metodo:
        doc.add_paragraph(f"Filtro Outlier applicato: Sigma {n_sigma}")

    for sezione in dati_report:
        doc.add_page_break() if dati_report.index(sezione) > 0 else None
        punto_nome = sezione['punto']
        doc.add_heading(f"Analisi Sensore: {punto_nome}", level=2)

        if sezione['img_path'] and os.path.exists(sezione['img_path']):
            doc.add_picture(sezione['img_path'], width=Inches(6.0))
        
        doc.add_heading(f"Metriche Calcolate - {punto_nome}", level=3)
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
    st.subheader("🛰️ DIMOS - Analisi Monitoraggio Topografico")
    
    uploaded_file = st.file_uploader("📂 Carica file Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        dfs = carica_excel(uploaded_file)
        fogli = list(dfs.keys())
        
        tutte_colonne = []
        for f in fogli:
            tutte_colonne.extend(estrai_colonne_numeriche(dfs[f]))
        colonne_uniche = sorted(list(set(tutte_colonne)))

        # --- SEZIONE 1: CONFIGURAZIONE VIDEO ---
        st.write("### 📺 Configurazione Visualizzazione e Trend (Video)")
        cv1, cv2, cv3 = st.columns([1.5, 1, 1])
        with cv1:
            punti_v = st.multiselect("Seleziona Sensori (Video)", fogli, key="pv")
            params_v = st.multiselect("Parametri (Video)", colonne_uniche, default=ottieni_default_params(colonne_uniche), key="prv")
        with cv2:
            metodo_v = st.radio("Metodo elaborazione (Video)", ["Dati Completi", "Filtro Sigma (Gauss)"], key="mv")
            ns_v = st.slider("Valore Sigma (Video)", 1.0, 5.0, 2.0, 0.5) if "Sigma" in metodo_v else 2.0
        with cv3:
            st.write("**Trend Polinomiale**")
            trend_v = st.checkbox("Inserisci Curva di Tendenza", value=False, key="tv")
            grado_v = st.slider("Grado del Polinomio", 1, 5, 2, key="gv") if trend_v else 1

        if punti_v and params_v:
            fig_v = go.Figure()
            for p in punti_v:
                df = dfs[p].copy()
                col_dt = df.columns[0]
                df[col_dt] = pd.to_datetime(df[col_dt], errors="coerce", dayfirst=True)
                df = df.dropna(subset=[col_dt]).sort_values(col_dt)
                for pr in params_v:
                    if pr not in df.columns: continue
                    d = df[[col_dt, pr]].copy()
                    d[pr] = converti_numerico(d[pr])
                    d = d.dropna()
                    if "Sigma" in metodo_v:
                        d[pr] = applica_filtro_sigma(d[pr], ns_v)
                        d = d.dropna()
                    if not d.empty:
                        fig_v.add_trace(go.Scatter(x=d[col_dt], y=d[pr], mode="lines+markers", name=f"{p}: {pr}"))
                        if trend_v:
                            tr = calcola_trend_polinomiale(d[col_dt], d[pr], grado_v)
                            if tr is not None:
                                fig_v.add_trace(go.Scatter(x=d[col_dt], y=tr, mode="lines", line=dict(dash='dash'), name=f"Trend {grado_v}° ({p})"))
            
            # Formattazione date in Italiano
            fig_v.update_xaxes(tickformat="%b %Y", tickformatstops=[dict(dtickrange=[None, None], value="%b %Y")])
            st.plotly_chart(fig_v, use_container_width=True)

        # --- SEZIONE 2: ESPORTAZIONE FILE WORD ---
        st.divider()
        st.write("### 📄 Configurazione Esportazione Report Word")
        w1, w2, w3 = st.columns([1.5, 1, 1])
        with w1:
            punti_w_raw = st.multiselect("Seleziona Sensori (Word)", ["TUTTI"] + fogli, default=punti_v, key="pw")
            params_w = st.multiselect("Parametri (Word)", colonne_uniche, default=params_v, key="prw")
        with w2:
            metodo_w = st.radio("Metodo elaborazione (Word)", ["Dati Completi", "Filtro Sigma (Gauss)"], key="mw")
            ns_w = st.slider("Valore Sigma (Word)", 1.0, 5.0, 2.0, 0.5) if "Sigma" in metodo_w else 2.0
        with w3:
            st.write("**Trend Polinomiale**")
            trend_w = st.checkbox("Inserisci Curva di Tendenza (Word)", value=False, key="tw")
            grado_w = st.slider("Grado del Polinomio (Word)", 1, 5, 2, key="gw") if trend_w else 1

        if st.button("🚀 Genera Grafici su file Word"):
            punti_effettivi = fogli if "TUTTI" in punti_w_raw else punti_w_raw
            if not punti_effettivi or not params_w:
                st.warning("Seleziona sensori e parametri per il report.")
            else:
                with st.spinner("Creazione grafici individuali per il report..."):
                    dati_per_report = []
                    for punto in punti_effettivi:
                        dfw = dfs[punto].copy()
                        c_dt = dfw.columns[0]
                        dfw[c_dt] = pd.to_datetime(dfw[c_dt], errors="coerce", dayfirst=True)
                        dfw = dfw.dropna(subset=[c_dt]).sort_values(c_dt)
                        
                        fig_p = go.Figure()
                        metriche_p = []
                        
                        for prm in params_w:
                            if prm not in dfw.columns: continue
                            dw = dfw[[c_dt, prm]].copy()
                            dw[prm] = converti_numerico(dw[prm])
                            dw = dw.dropna()
                            if "Sigma" in metodo_w:
                                dw[prm] = applica_filtro_sigma(dw[prm], ns_w)
                                dw = dw.dropna()
                            
                            if not dw.empty:
                                metriche_p.append({
                                    "parametro": prm, "min": dw[prm].min(), "max": dw[prm].max(), 
                                    "range": dw[prm].max() - dw[prm].min(), "ultimo": dw[prm].iloc[-1]
                                })
                                fig_p.add_trace(go.Scatter(x=dw[c_dt], y=dw[prm], mode="lines+markers", name=prm))
                                if trend_w:
                                    trw = calcola_trend_polinomiale(dw[c_dt], dw[prm], grado_w)
                                    if trw is not None:
                                        fig_p.add_trace(go.Scatter(x=dw[c_dt], y=trw, mode="lines", line=dict(dash='dash'), name=f"Trend {grado_w}°"))

                        if metriche_p:
                            fig_p.update_layout(title=f"Sensore: {punto}", template="plotly_white")
                            # Date in italiano anche nel grafico Word
                            fig_p.update_xaxes(tickformat="%b %Y")
                            
                            img_t = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            fig_p.write_image(img_t.name, width=1000, height=500)
                            dati_per_report.append({"punto": punto, "metriche": metriche_p, "img_path": img_t.name})

                    if dati_per_report:
                        path_w = genera_report_word_separato(metodo_w, ns_w, dati_per_report)
                        with open(path_w, "rb") as f:
                            st.download_button("⬇️ Scarica Report Word", f, "Report_Monitoring Survey DIMOS_.docx")

if __name__ == "__main__":
    run_tps_monitoring()
