import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from datetime import datetime
from io import BytesIO

# --- GESTIONE LIBRERIE STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    WORD_OK = True
except ImportError:
    WORD_OK = False

# --- CACHE DATI ---
@st.cache_data(show_spinner=False)
def carica_file_cache(uploaded_file):
    df_name = None
    if uploaded_file.name.endswith(('.xlsx', '.xlsm')):
        xls = pd.ExcelFile(uploaded_file)
        if "NAME" in xls.sheet_names:
            df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        sheet_dati = [s for s in xls.sheet_names if s not in ["NAME", "Info", "ARRAY"]][0]
        df_dati = pd.read_excel(xls, sheet_name=sheet_dati)
    else:
        df_dati = pd.read_csv(uploaded_file, sep=None, engine='python')
    
    col_t = df_dati.columns[0]
    df_dati[col_t] = pd.to_datetime(df_dati[col_t], dayfirst=True, errors='coerce')
    df_dati = df_dati.dropna(subset=[col_t]).sort_values(col_t)
    return df_dati, df_name

# --- MOTORE PULIZIA E PARSING ---
def pulisci_dati(serie, n_sigma, drop_zeros):
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

def parse_column_info(col_name, df_name=None, col_index=None):
    if df_name is not None and col_index is not None:
        try:
            dl = str(df_name.iloc[0, col_index]).strip()
            sens = str(df_name.iloc[1, col_index]).strip()
            web_info = str(df_name.iloc[2, col_index]).strip() if len(df_name) > 2 else col_name
            unit_m = re.search(r'\[(.*?)\]', web_info)
            unit = f" [{unit_m.group(1)}]" if unit_m else ""
            p_match = re.search(r'_(X|Y|Z|T1|T2|LI|LQ|LM|VAR\d+)', web_info)
            param = p_match.group(1) if p_match else web_info.split()[-1].replace(unit.strip(), "").strip()
            return dl, sens, f"{param}{unit}"
        except: pass
    unit_m = re.search(r'\[(.*?)\]', col_name)
    unit = f" [{unit_m.group(1)}]" if unit_m else ""
    parts = re.sub(r'\[.*?\]', '', col_name).strip().split()
    dl = parts[0] if len(parts) > 0 else "DL"
    if len(parts) > 1:
        s_parts = parts[1].rsplit('_', 1)
        if len(s_parts) > 1 and len(s_parts[1]) <= 3: sens_base, param = s_parts[0], s_parts[1]
        else: sens_base, param = parts[1], "Dato"
    else: sens_base, param = "Generico", "Dato"
    return dl, sens_base, f"{param}{unit}"

def run_plotter():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")
    st.divider()

    # --- SIDEBAR PARAMETRI ---
    with st.sidebar:
        st.header("⚙️ Parametri Tecnici")
        sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
        rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
        show_trend = st.checkbox("Mostra Linea di Tendenza (3° grado)", value=True)
        st.divider()

    uploaded_file = st.file_uploader("📂 Carica file Excel o CSV", type=['xlsx', 'xlsm', 'csv'])

    if uploaded_file:
        df_dati, df_name = carica_file_cache(uploaded_file)
        col_t = df_dati.columns[0]
        
        # Sincronizzazione per Modulo Mappe
        st.session_state['df_values'] = df_dati
        st.session_state['col_tempo'] = col_t

        gerarchia = {}
        for i, col in enumerate(df_dati.columns):
            if i == 0: continue
            dl, sens, param = parse_column_info(col, df_name, i)
            if dl not in gerarchia: gerarchia[dl] = {}
            if sens not in gerarchia[dl]: gerarchia[dl][sens] = {}
            gerarchia[dl][sens][param] = col

        # --- SEZIONE VISUALIZZAZIONE GRAFICO ---
        st.subheader("📊 Visualizzazione Grafica Dinamica")
        cv1, cv2, cv3 = st.columns(3)
        with cv1: sel_dl_v = st.multiselect("1. Datalogger (Vis)", sorted(gerarchia.keys()))
        with cv2:
            s_opts_v = sorted(list(set([s for d in sel_dl_v for s in gerarchia[d].keys()])))
            sel_sens_v = st.multiselect("2. Sensori (Vis)", s_opts_v)
        with cv3:
            p_opts_v = sorted(list(set([p for d in sel_dl_v for s in sel_sens_v if s in gerarchia[d] for p in gerarchia[d][s].keys()])))
            sel_params_v = st.multiselect("3. Grandezze (Vis)", p_opts_v)

        if sel_params_v:
            fig = go.Figure()
            colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692"]
            report_stats = []
            
            for d in sel_dl_v:
                for s in sel_sens_v:
                    if s in gerarchia[d]:
                        for p in sel_params_v:
                            if p in gerarchia[d][s]:
                                col_id = gerarchia[d][s][p]
                                color = colors[len(report_stats) % len(colors)]
                                y_v, diag = pulisci_dati(df_dati[col_id], sigma_val, rimuovi_zeri)
                                diag["Parametro"] = f"{s} - {p}"
                                report_stats.append(diag)
                                
                                fig.add_trace(go.Scatter(x=df_dati[col_t], y=y_v, name=f"{s}-{p}",
                                    mode='lines+markers', line=dict(color=color, width=1.3), marker=dict(size=3)))
                                
                                if show_trend:
                                    v_idx = y_v.notna()
                                    if v_idx.sum() > 4:
                                        x_ts = df_dati.loc[v_idx, col_t].apply(lambda x: x.timestamp())
                                        poly = np.poly1d(np.polyfit(x_ts, y_v[v_idx], 3))
                                        fig.add_trace(go.Scatter(x=df_dati[col_t], y=poly(df_dati[col_t].apply(lambda x: x.timestamp())),
                                            name=f"Trend {s}-{p}", line=dict(color=color, width=2, dash='dash'), opacity=0.4))

            fig.update_layout(height=650, template="plotly_white", xaxis=dict(rangeslider=dict(visible=True)), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})
            st.table(pd.DataFrame(report_stats).set_index("Parametro"))

        # --- SEZIONE STAMPA WORD (CON IMMAGINI CORRETTE) ---
        st.divider()
        st.subheader("📄 Configurazione Stampa Word")
        with st.container(border=True):
            cw1, cw2, cw3 = st.columns(3)
            with cw1: sel_dl_w = st.multiselect("1. Datalogger (Stampa)", sorted(gerarchia.keys()))
            with cw2:
                s_opts_w = sorted(list(set([s for d in sel_dl_w for s in gerarchia[d].keys()])))
                sel_sens_w = st.multiselect("2. Sensori (Stampa)", s_opts_w)
            with cw3:
                p_opts_w = sorted(list(set([p for d in sel_dl_w for s in sel_sens_w if s in gerarchia[d] for p in gerarchia[d][s].keys()])))
                sel_params_w = st.multiselect("3. Grandezze (Stampa)", p_opts_w)

            if st.button("🚀 Genera Report Word con Grafici") and WORD_OK:
                doc = Document()
                doc.add_heading('Report Monitoraggio DIMOS', 0)
                
                for d in sel_dl_w:
                    doc.add_heading(f'Centralina: {d}', level=1)
                    for s in sel_sens_w:
                        if s in gerarchia[d]:
                            p_finali = [p for p in sel_params_w if p in gerarchia[d][s]]
                            if p_finali:
                                doc.add_heading(f'Sensore: {s}', level=2)
                                for p in p_finali:
                                    col_id = gerarchia[d][s][p]
                                    y_c, diag = pulisci_dati(df_dati[col_id], sigma_val, rimuovi_zeri)
                                    
                                    # Generazione Grafico Matplotlib per Word
                                    plt.figure(figsize=(10, 4))
                                    plt.plot(df_dati[col_t], y_c, label=f"{p}", color='blue', linewidth=1)
                                    
                                    if show_trend and y_c.notna().sum() > 4:
                                        x_ts = df_dati.loc[y_c.notna(), col_t].apply(lambda x: x.timestamp())
                                        poly = np.poly1d(np.polyfit(x_ts, y_c.dropna(), 3))
                                        plt.plot(df_dati[col_t], poly(df_dati[col_t].apply(lambda x: x.timestamp())), 
                                                 color='red', linestyle='--', label='Trend')
                                    
                                    plt.title(f"{s} - {p}")
                                    plt.grid(True, alpha=0.3)
                                    plt.gcf().autofmt_xdate()
                                    
                                    img_stream = BytesIO()
                                    plt.savefig(img_stream, format='png', bbox_inches='tight', dpi=100)
                                    plt.close()
                                    img_stream.seek(0) # <--- PUNTO CRUCIALE RIPRISTINATO
                                    
                                    doc.add_paragraph(f"Parametro: {p} | Zeri: {diag['zeri']} | Gauss: {diag['gauss']}")
                                    doc.add_picture(img_stream, width=Inches(6))
                
                buf = BytesIO()
                doc.save(buf)
                st.download_button("⬇️ Scarica File Word", buf.getvalue(), "Report_Monitoraggio.docx")

if __name__ == "__main__":
    run_plotter()
