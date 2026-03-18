import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import re

# --- GESTIONE LIBRERIA DOCX ---
try:
    from docx import Document
    from docx.shared import Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- FUNZIONE PULIZIA STRINGHE (Cruciale per evitare KeyError) ---
def clean_column_name(s):
    if pd.isna(s): return ""
    # Rimuove spazi multipli, spazi ai bordi e normalizza caratteri speciali comuni
    s = str(s).strip().replace("  ", " ")
    # Rimuove caratteri "fantasma" spesso presenti nei CSV (es. 蚓 invece di °C)
    s = re.sub(r'[^\x00-\x7F]+', ' ', s) 
    return s.strip()

# --- LOGICA FILTRI ---
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

# --- PARSING GERARCHICO ---
def parse_hierarchy(df_header):
    tree = {}
    for col_idx in range(1, len(df_header.columns)):
        r1 = clean_column_name(df_header.iloc[0, col_idx])
        r2 = clean_column_name(df_header.iloc[1, col_idx])
        r3 = clean_column_name(df_header.iloc[2, col_idx])
        
        if not r3 or r3 == "nan": continue

        # Fallback basato sulla tua logica: Centralina/Sensore da riga 3
        parts = r3.split()
        web_id = parts[0] if len(parts) > 0 else f"Col_{col_idx}"
        
        centralina = r1 if r1 not in ["", "nan", "datalogger"] else web_id
        
        if r2 and r2 != "nan":
            sensore = r2
        else:
            if "BATT" in r3: sensore = "Diagnostica Batteria"
            elif "CL_" in r3: 
                sub = r3.split('_')
                sensore = f"{sub[1]}_{sub[2]}" if len(sub) > 2 else web_id
            else: sensore = "Sensore_" + web_id

        if centralina not in tree: tree[centralina] = {}
        if sensore not in tree[centralina]: tree[centralina][sensore] = {}
        
        label_canale = " ".join(parts[1:]) if len(parts) > 1 else r3
        tree[centralina][sensore][r3] = label_canale
    return tree

def main():
    st.set_page_config(layout="wide", page_title="Plotter RFI Campi Flegrei")
    st.title("🛰️ Analisi Gerarchica Sensori")

    with st.sidebar:
        st.header("1. Caricamento")
        f_name = st.file_uploader("File NAME (Metadati)", type=['csv'])
        f_data = st.file_uploader("File DATI", type=['csv'])
        st.divider()
        st.header("2. Visualizzazione")
        tipo_asse = st.radio("Modalità Asse X:", ["Temporale Reale", "Testo Sequenziale"])
        passo = st.number_input("Etichette ogni N righe:", 1, 5000, 100)
        st.divider()
        st.header("3. Filtri Statistici")
        sigma = st.slider("Gauss (Sigma)", 0.0, 5.0, 2.5)
        rimuovi_zeri = st.toggle("Escludi Zeri Puri", value=True)

    if f_name and f_data:
        # Caricamento con rilevamento automatico separatore
        df_h = pd.read_csv(f_name, sep=None, engine='python', header=None, nrows=3)
        df_v = pd.read_csv(f_data, sep=None, engine='python')
        
        # Pulizia Nomi Colonne Dati
        df_v.columns = [clean_column_name(c) for c in df_v.columns]
        col_t = df_v.columns[0]
        df_v[col_t] = pd.to_datetime(df_v[col_t], errors='coerce')
        df_v = df_v.dropna(subset=[col_t]).sort_values(by=col_t)

        tree = parse_hierarchy(df_h)

        # --- INTERFACCIA DI SCELTA ---
        c1, c2 = st.columns(2)
        with c1:
            cent_sel = st.selectbox("Seleziona Centralina:", sorted(tree.keys()))
        with c2:
            sens_sel = st.multiselect("Seleziona Sensore/i:", sorted(tree[cent_sel].keys()))

        targets = []
        if sens_sel:
            st.write("### Selezione Parametri")
            cols = st.columns(len(sens_sel))
            for i, s in enumerate(sens_sel):
                with cols[i]:
                    st.markdown(f"**{s}**")
                    for cid, label in tree[cent_sel][s].items():
                        # Controllo se il CID ripulito esiste nelle colonne dei dati
                        if cid in df_v.columns:
                            if st.checkbox(label, key=cid, value=True):
                                targets.append((s, cid, label))
                        else:
                            st.caption(f"⚠️ {label} (non trovato)")

        if targets:
            # Range Date
            dr = st.date_input("Periodo:", [df_v[col_t].min().date(), df_v[col_t].max().date()])
            if len(dr) == 2:
                df_p = df_v[(df_v[col_t].dt.date >= dr[0]) & (df_v[col_t].dt.date <= dr[1])].copy().reset_index()

                fig = go.Figure()
                stats_final = {}

                for s_name, cid, label in targets:
                    y_f, diag = applica_filtri_completi(df_p[cid], sigma, rimuovi_zeri)
                    tag = f"{s_name}: {label}"
                    stats_final[tag] = diag
                    
                    x_axis = df_p.index if tipo_asse == "Testo Sequenziale" else df_p[col_t]
                    fig.add_trace(go.Scatter(x=x_axis, y=y_f, name=tag, mode='lines+markers'))

                if tipo_asse == "Testo Sequenziale":
                    ticks = [df_p.iloc[i][col_t].strftime('%d/%m %H:%M') if i % passo == 0 else "" for i in range(len(df_p))]
                    fig.update_xaxes(tickmode='array', tickvals=list(df_p.index), ticktext=ticks, tickangle=-45)

                fig.update_layout(template="plotly_white", height=600, hovermode="x unified", legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)

                # Tabella Diagnostica
                with st.expander("📊 Diagnostica Gauss e Zeri"):
                    st.table(pd.DataFrame(stats_final).T)

if __name__ == "__main__":
    main()
