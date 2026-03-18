import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# --- GESTIONE LIBRERIA DOCX ---
try:
    from docx import Document
    from docx.shared import Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- LOGICA FILTRI (GAUSS E ZERI) ---
def applica_filtri_completi(serie, n_sigma, rimuovi_zeri):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    
    if rimuovi_zeri:
        diag["zeri"] = (originale == 0).sum()
        originale = originale.replace(0, np.nan)
    
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        mean, std = validi.mean(), validi.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diag["gauss"] = outliers.sum()
            originale[outliers] = np.nan
            
    return originale, diag

# --- PARSING GERARCHICO INTELLIGENTE ---
def parse_hierarchy(df_header):
    tree = {}
    for col_idx in range(1, len(df_header.columns)):
        r1 = str(df_header.iloc[0, col_idx]).strip() # Centralina
        r2 = str(df_header.iloc[1, col_idx]).strip() # Sensore
        r3 = str(df_header.iloc[2, col_idx]).strip() # Canale/Dato
        
        if r3 == "nan" or not r3: continue

        # Fallback Centralina/Sensore da riga 3 (es: CO_9286 BATT [V])
        parts = r3.split()
        prefix = parts[0] if len(parts) > 0 else f"Unknown_{col_idx}"
        
        nome_centralina = r1 if r1 not in ["nan", "", "datalogger"] else prefix
        
        if r2 not in ["nan", ""]:
            nome_sensore = r2
        else:
            # Estrazione tipo sensore dal nome web (es. CL_01 o BATT)
            if "BATT" in r3: nome_sensore = "Diagnostica Batteria"
            elif "CL_" in r3: nome_sensore = "_".join(r3.split('_')[1:3])
            else: nome_sensore = "Sensore_" + prefix

        if nome_centralina not in tree: tree[nome_centralina] = {}
        if nome_sensore not in tree[nome_centralina]: tree[nome_centralina][nome_sensore] = {}
        
        # Etichetta del canale (quello che resta dopo il prefisso)
        label_canale = " ".join(parts[1:]) if len(parts) > 1 else r3
        tree[nome_centralina][nome_sensore][r3] = label_canale
    return tree

# --- FUNZIONE REPORT WORD ---
def genera_report_word(fig, stats, d_range, sigma, zeri_on):
    doc = Document()
    doc.add_heading('REPORT MONITORAGGIO TECNICO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    info = doc.add_paragraph()
    info.add_run(f"Data Report: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n").bold = True
    info.add_run(f"Periodo Analisi: {d_range[0]} - {d_range[1]}\n")
    info.add_run(f"Filtri: Gauss {sigma}σ | Rimozione Zeri: {'Sì' if zeri_on else 'No'}")

    img_bytes = fig.to_image(format="png", width=1000, height=550)
    doc.add_picture(BytesIO(img_bytes), width=Inches(6))

    doc.add_heading('Diagnostica Dati Rimossi', level=1)
    table = doc.add_table(rows=1, cols=3); table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = 'Canale', 'Zeri Rimossi', 'Outliers Gauss'
    for lab, d in stats.items():
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = lab, str(d['zeri']), str(d['gauss'])
    
    target = BytesIO()
    doc.save(target)
    return target.getvalue()

# --- INTERFACCIA STREAMLIT ---
def main():
    st.set_page_config(layout="wide", page_title="Plotter RFI Elegante")
    st.title("📉 Plotter Geotecnico Multi-Livello")

    with st.sidebar:
        st.header("📂 Sorgenti")
        f_name = st.file_uploader("Layer NAME (Metadati)", type=['csv', 'xlsx'])
        f_data = st.file_uploader("File DATI (flegrei)", type=['csv', 'xlsx'])
        st.divider()
        st.header("🔍 Parametri Analisi")
        tipo_asse = st.radio("Modalità Asse X:", ["Temporale Reale", "Sequenziale (Testo)"])
        passo = st.number_input("Etichette ogni N righe:", value=100) if tipo_asse == "Sequenziale (Testo)" else 0
        rimuovi_zeri = st.toggle("Filtro Zeri Puri", value=True)
        sigma = st.slider("Filtro Gauss (Deviazioni σ)", 0.0, 5.0, 2.0)
        
    if f_name and f_data:
        # Lettura (adattata per CSV con ;)
        df_h = pd.read_csv(f_name, sep=';', header=None, nrows=3)
        df_v = pd.read_csv(f_data, sep=';')
        
        col_t = df_v.columns[0]
        df_v[col_t] = pd.to_datetime(df_v[col_t], errors='coerce')
        df_v = df_v.dropna(subset=[col_t]).sort_values(by=col_t)

        tree = parse_hierarchy(df_h)

        # --- SELEZIONE ELEGANTE ---
        st.info("Seleziona la gerarchia da visualizzare:")
        c1, c2 = st.columns(2)
        with c1:
            cent_sel = st.selectbox("1. Centralina:", sorted(tree.keys()))
        with c2:
            sens_sel = st.multiselect("2. Sensori:", sorted(tree[cent_sel].keys()))

        targets = []
        if sens_sel:
            st.write("3. Canali specifici:")
            cols = st.columns(len(sens_sel))
            for i, s in enumerate(sens_sel):
                with cols[i]:
                    st.caption(f"**{s}**")
                    for cid, lab in tree[cent_sel][s].items():
                        if st.checkbox(lab if lab else cid, key=cid, value=True):
                            targets.append((s, cid, lab))

        if targets:
            # Filtro Date
            st.divider()
            dr = st.date_input("Periodo:", [df_v[col_t].min().date(), df_v[col_t].max().date()])
            if len(dr) == 2:
                mask = (df_v[col_t].dt.date >= dr[0]) & (df_v[col_t].dt.date <= dr[1])
                df_p = df_v[mask].copy().reset_index()

                # Grafico
                fig = go.Figure()
                stats_final = {}

                for s_name, cid, label in targets:
                    y_f, diag = applica_filtri_completi(df_p[cid], sigma, rimuovi_zeri)
                    full_label = f"{s_name} - {label}"
                    stats_final[full_label] = diag
                    
                    x_axis = df_p.index if tipo_asse == "Sequenziale (Testo)" else df_p[col_t]
                    fig.add_trace(go.Scatter(x=x_axis, y=y_f, name=full_label, mode='lines+markers', connectgaps=True))

                # Formattazione Asse X Sequenziale (Grafico Dinamico)
                if tipo_asse == "Sequenziale (Testo)":
                    ticks = [df_p.iloc[i][col_t].strftime('%d/%m %H:%M') if i % passo == 0 else "" for i in range(len(df_p))]
                    fig.update_xaxes(tickmode='array', tickvals=list(df_p.index), ticktext=ticks, tickangle=-45)

                fig.update_layout(template="plotly_white", height=600, hovermode="x unified", legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)

                # Diagnostica e Export
                ex1, ex2 = st.columns([2, 1])
                with ex1:
                    with st.expander("📊 Risultati Analisi di Gauss"):
                        st.table(pd.DataFrame(stats_final).T)
                with ex2:
                    if st.button("📝 Genera Report Word"):
                        if DOCX_AVAILABLE:
                            wb = genera_report_word(fig, stats_final, dr, sigma, rimuovi_zeri)
                            st.download_button("📥 Scarica Report", wb, f"Report_{cent_sel}.docx")
                        else:
                            st.error("Modulo docx non trovato.")

if __name__ == "__main__":
    main()
