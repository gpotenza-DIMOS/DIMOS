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
# SETUP E UTILITY
# =========================================================
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DIMOS")

def converti_numerico(serie):
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False).str.replace(" ", "", regex=False), errors="coerce")

def applica_filtro_sigma(serie, n_sigma=2.0):
    try:
        serie = converti_numerico(serie)
        media, std = serie.mean(), serie.std()
        if pd.isna(std) or std == 0: return serie
        return serie.where((serie >= media - n_sigma * std) & (serie <= media + n_sigma * std))
    except: return serie

@st.cache_data
def carica_excel(uploaded_file):
    data = {}
    xl = pd.ExcelFile(uploaded_file, engine="openpyxl")
    for sheet in xl.sheet_names:
        df = xl.parse(sheet, header=0).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]
        data[sheet] = df
    return data

def estrai_colonne_numeriche(df):
    return [c for c in df.columns[1:] if "Unnamed" not in str(c) and converti_numerico(df[c]).notnull().sum() > 0]

# =========================================================
# MOTORE DI ELABORAZIONE (Condiviso tra UI e Word)
# =========================================================
def elabora_analisi(config_dict, dfs, metodo, n_sigma):
    """
    Ritorna: (figura_plotly, lista_metriche)
    """
    fig = go.Figure()
    metriche = []
    
    for punto, parametri in config_dict.items():
        if not parametri: continue
        df = dfs[punto].copy()
        col_data = df.columns[0]
        df[col_data] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)
        df = df.dropna(subset=[col_data]).sort_values(col_data)

        for parametro in parametri:
            d = df[[col_data, parametro]].copy()
            d[parametro] = converti_numerico(d[parametro])
            d = d.dropna()
            if metodo == "Filtro Sigma (Gauss)":
                d[parametro] = applica_filtro_sigma(d[parametro], n_sigma)
                d = d.dropna()
            
            if d.empty: continue
            
            # Calcolo Metriche
            min_v, max_v, last_v = d[parametro].min(), d[parametro].max(), d[parametro].iloc[-1]
            metriche.append({
                "punto": punto, "parametro": parametro,
                "min": min_v, "max": max_v, "range": max_v - min_v, "ultimo": last_v
            })

            # Grafico
            fig.add_trace(go.Scatter(x=d[col_data], y=d[parametro], mode="lines+markers", name=f"{punto}: {parametro}"))
            
    fig.update_layout(template="plotly_white", height=600, hovermode="x unified", legend=dict(orientation="h", y=1.05))
    return fig, metriche

# =========================================================
# APP PRINCIPALE
# =========================================================
def main():
    st.set_page_config(page_title="DIMOS - Analisi Topografica", layout="wide")
    st.title("🛰️ DIMOS - Analisi Topografica Avanzata")

    uploaded_file = st.file_uploader("📂 Carica file Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        dfs = carica_excel(uploaded_file)
        fogli = list(dfs.keys())

        # --- SEZIONE 1: CONFIGURAZIONE VISUALIZZAZIONE ---
        with st.expander("📺 CONFIGURAZIONE VISUALIZZAZIONE (Dashboard)", expanded=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                punti_ui = st.multiselect("Sensori da visualizzare", fogli, key="ui_punti")
            with c2:
                metodo_ui = st.radio("Filtro UI", ["Dati Completi", "Filtro Sigma"], horizontal=True, key="ui_metodo")
                sigma_ui = st.slider("Sigma UI", 1.0, 5.0, 2.0, key="ui_sigma") if metodo_ui == "Filtro Sigma" else 2.0

            config_ui = {}
            if punti_ui:
                cols = st.columns(len(punti_ui))
                for i, p in enumerate(punti_ui):
                    with cols[i]:
                        config_ui[p] = st.multiselect(f"Parametri {p}", estrai_colonne_numeriche(dfs[p]), key=f"ui_p_{p}")

        # --- ESECUZIONE VISUALIZZAZIONE ---
        if any(config_ui.values()):
            fig_ui, metriche_ui = elabora_analisi(config_ui, dfs, metodo_ui, sigma_ui)
            
            st.subheader("📊 Analisi Interattiva")
            m_cols = st.columns(4)
            for idx, m in enumerate(metriche_ui):
                m_cols[idx % 4].metric(f"{m['punto']} | {m['parametro']}", f"{m['ultimo']:.3f}", f"R: {m['range']:.3f}")
            
            st.plotly_chart(fig_ui, use_container_width=True)

        st.divider()

        # --- SEZIONE 2: CONFIGURAZIONE ESPORTAZIONE WORD ---
        with st.expander("📄 CONFIGURAZIONE REPORT WORD (Esportazione)", expanded=False):
            st.info("Qui puoi selezionare punti e parametri diversi da quelli visualizzati sopra per il tuo file finale.")
            
            cw1, cw2 = st.columns([2, 1])
            with cw1:
                punti_doc = st.multiselect("Sensori da includere nel REPORT", fogli, key="doc_punti")
            with cw2:
                metodo_doc = st.radio("Filtro REPORT", ["Dati Completi", "Filtro Sigma"], horizontal=True, key="doc_metodo")
                sigma_doc = st.slider("Sigma REPORT", 1.0, 5.0, 2.0, key="doc_sigma") if metodo_doc == "Filtro Sigma" else 2.0

            config_doc = {}
            if punti_doc:
                cols_doc = st.columns(len(punti_doc))
                for i, p in enumerate(punti_doc):
                    with cols_doc[i]:
                        config_doc[p] = st.multiselect(f"Parametri REPORT {p}", estrai_colonne_numeriche(dfs[p]), key=f"doc_p_{p}")

            if st.button("🚀 GENERA E SCARICA REPORT WORD"):
                if not any(config_doc.values()):
                    st.error("Seleziona almeno un parametro per il report!")
                else:
                    with st.spinner("Generazione Report in corso..."):
                        # Elaborazione specifica per il Word
                        fig_doc, metriche_doc = elabora_analisi(config_doc, dfs, metodo_doc, sigma_doc)
                        
                        # Salvataggio immagine temporanea
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                            fig_doc.write_image(tmp_img.name, width=1200, height=700)
                            
                            # Creazione Documento
                            doc = Document()
                            doc.add_heading('DIMOS - REPORT TECNICO', 0)
                            doc.add_paragraph(f"Metodo elaborazione: {metodo_doc} (Sigma: {sigma_doc})")
                            
                            doc.add_heading('Grafico di Analisi', level=1)
                            doc.add_picture(tmp_img.name, width=Inches(6.2))
                            
                            doc.add_heading('Tabella Metriche', level=1)
                            table = doc.add_table(rows=1, cols=6)
                            table.style = 'Table Grid'
                            for i, h in enumerate(["Punto", "Parametro", "MIN", "MAX", "RANGE", "ULTIMO"]):
                                table.rows[0].cells[i].text = h
                            
                            for m in metriche_doc:
                                row = table.add_row().cells
                                row[0].text = str(m['punto'])
                                row[1].text = str(m['parametro'])
                                row[2].text = f"{m['min']:.3f}"
                                row[3].text = f"{m['max']:.3f}"
                                row[4].text = f"{m['range']:.3f}"
                                row[5].text = f"{m['ultimo']:.3f}"

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_doc:
                                doc.save(tmp_doc.name)
                                with open(tmp_doc.name, "rb") as f:
                                    st.download_button("⬇️ Clicca qui per scaricare il Word", f, "Report_Dimos_Personalizzato.docx")

    else:
        st.info("Carica un file Excel per attivare i pannelli di configurazione.")

if __name__ == "__main__":
    main()
