import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import re
from datetime import datetime
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    WORD_OK = True
except ImportError:
    WORD_OK = False

@st.cache_data(show_spinner=False)
def carica_file_cache(uploaded_file):
    df_name = None
    try:
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
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None, None

def pulisci_dati(serie, n_sigma, drop_zeros):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    try:
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
    except:
        pass # Se il filtro fallisce, restituisce il dato grezzo per non bloccare il grafico
    return originale, diag

def parse_column_info(col_name, df_name=None, col_index=None):
    if df_name is not None and col_index is not None:
        try:
            dl = str(df_name.iloc[0, col_index]).strip()
            sens = str(df_name.iloc[1, col_index]).strip()
            web_info = str(df_name.iloc[2, col_index]).strip()
            unit_m = re.search(r'\[(.*?)\]', web_info)
            unit = f" [{unit_m.group(1)}]" if unit_m else ""
            p_match = re.search(r'_(X|Y|Z|T1|T2|LI|LQ|LM|VAR\d+)', web_info)
            param = p_match.group(1) if p_match else web_info.split()[-1].replace(unit.strip(), "").strip()
            return dl, sens, f"{param}{unit}"
        except: pass
    return "DL", "Generico", col_name

def run_plotter():
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    st.markdown("# Monitoraggio DIMOS - Analisi Dati")

    with st.sidebar:
        st.header("⚙️ Filtri")
        sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
        rimuovi_zeri = st.checkbox("Rimuovi '0'", value=True)
        show_trend = st.checkbox("Trend Polinomiale (3°)", value=True)

    uploaded_file = st.file_uploader("📂 Carica file", type=['xlsx', 'xlsm', 'csv'])

    if uploaded_file:
        df_dati, df_name = carica_file_cache(uploaded_file)
        if df_dati is None: return
        
        col_t = df_dati.columns[0]
        gerarchia = {}
        for i, col in enumerate(df_dati.columns):
            if i == 0: continue
            dl, sens, param = parse_column_info(col, df_name, i)
            if dl not in gerarchia: gerarchia[dl] = {}
            if sens not in gerarchia[dl]: gerarchia[dl][sens] = {}
            gerarchia[dl][sens][param] = col

        # --- VISUALIZZAZIONE SCHERMO ---
        st.subheader("📊 Analisi Grafica")
        cv1, cv2, cv3 = st.columns(3)
        with cv1: sel_dl_v = st.multiselect("Datalogger", sorted(gerarchia.keys()))
        with cv2:
            s_opts_v = sorted(list(set([s for d in sel_dl_v for s in gerarchia[d].keys()])))
            sel_sens_v = st.multiselect("Sensori", s_opts_v)
        with cv3:
            p_opts_v = sorted(list(set([p for d in sel_dl_v for s in sel_sens_v if s in gerarchia[d] for p in gerarchia[d][s].keys()])))
            sel_params_v = st.multiselect("Grandezze", p_opts_v)

        if sel_params_v:
            fig = go.Figure()
            for d in sel_dl_v:
                for s in sel_sens_v:
                    if s in gerarchia[d]:
                        for p in sel_params_v:
                            if p in gerarchia[d][s]:
                                y_v, _ = pulisci_dati(df_dati[gerarchia[d][s][p]], sigma_val, rimuovi_zeri)
                                if not y_v.dropna().empty:
                                    fig.add_trace(go.Scatter(x=df_dati[col_t], y=y_v, name=f"{s}-{p}", mode='lines'))
                                    if show_trend:
                                        v_idx = y_v.notna()
                                        if v_idx.sum() > 4:
                                            x_ts = df_dati.loc[v_idx, col_t].apply(lambda x: x.timestamp())
                                            poly = np.poly1d(np.polyfit(x_ts, y_v[v_idx], 3))
                                            fig.add_trace(go.Scatter(x=df_dati[col_t], y=poly(df_dati[col_t].apply(lambda x: x.timestamp())),
                                                name=f"Trend {s}", line=dict(color="red", dash='dash')))
            fig.update_layout(template="plotly_white", height=600)
            st.plotly_chart(fig, use_container_width=True)

        # --- REPORT WORD ---
        st.divider()
        st.subheader("📄 Genera Report")
        with st.expander("Scegli sensori per Word"):
            cw1, cw2, cw3 = st.columns(3)
            with cw1: sel_dl_w = st.multiselect("Datalogger", sorted(gerarchia.keys()), key="w1")
            with cw2:
                s_opts_w = sorted(list(set([s for d in sel_dl_w for s in gerarchia[d].keys()])))
                sel_sens_w = st.multiselect("Sensori", s_opts_w, key="w2")
            with cw3:
                p_opts_w = sorted(list(set([p for d in sel_dl_w for s in sel_sens_w if s in gerarchia[d] for p in gerarchia[d][s].keys()])))
                sel_params_w = st.multiselect("Grandezze", p_opts_w, key="w3")

        if st.button("🚀 Esporta Word") and WORD_OK:
            doc = Document()
            doc.add_heading('Report Monitoraggio DIMOS', 0)
            
            for d in sel_dl_w:
                doc.add_heading(f'Centralina: {d}', level=1)
                for s in sel_sens_w:
                    if s in gerarchia[d]:
                        for p in sel_params_w:
                            if p in gerarchia[d][s]:
                                y_c, diag = pulisci_dati(df_dati[gerarchia[d][s][p]], sigma_val, rimuovi_zeri)
                                if y_c.dropna().empty: continue
                                
                                doc.add_heading(f'Sensore: {s} - {p}', level=2)
                                doc.add_paragraph(f"Note: Zeri rimossi: {diag['zeri']} | Outliers Gauss: {diag['gauss']}")
                                
                                # GRAFICO MATPLOTLIB (STABILE)
                                plt.figure(figsize=(10, 6))
                                plt.plot(df_dati[col_t], y_c, label='Dati Rilevati', color='#1f77b4', marker='.', markersize=3, alpha=0.7)
                                
                                if show_trend:
                                    v_idx = y_c.notna()
                                    if v_idx.sum() > 10:
                                        x_ts = df_dati.loc[v_idx, col_t].apply(lambda x: x.timestamp())
                                        poly = np.poly1d(np.polyfit(x_ts, y_c[v_idx], 3))
                                        plt.plot(df_dati[col_t], poly(df_dati[col_t].apply(lambda x: x.timestamp())), 
                                                 color='red', linestyle='--', linewidth=2, label='Trend Polinomiale')
                                
                                plt.title(f"Monitoraggio {s} - {p}", fontsize=14, pad=15)
                                plt.grid(True, linestyle=':', alpha=0.6)
                                plt.legend(loc='best')
                                plt.gcf().autofmt_xdate() # Formatta le date sull'asse X
                                
                                img_buf = BytesIO()
                                plt.savefig(img_buf, format='png', dpi=120, bbox_inches='tight')
                                plt.close()
                                doc.add_picture(img_buf, width=Inches(6))
            
            output = BytesIO()
            doc.save(output)
            st.download_button("⬇️ Scarica Documento", output.getvalue(), "Report.docx")

if __name__ == "__main__":
    run_plotter()
