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
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- NORMALIZZAZIONE AGGRESSIVA (Risolve KeyError) ---
def normalize_string(s):
    if pd.isna(s): return ""
    # Tiene solo lettere, numeri e underscore per il confronto tecnico
    s = str(s).upper().strip()
    return re.sub(r'[^A-Z0-9_]', '', s)

def clean_label(s):
    if pd.isna(s): return ""
    # Pulisce i caratteri strani per la visualizzazione nel grafico
    return str(s).replace('蚓', '°C').strip()

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

def main():
    st.set_page_config(layout="wide", page_title="Plotter RFI Campi Flegrei")
    st.title("📉 Analisi Geotecnica (Versione Corretta)")

    with st.sidebar:
        st.header("📂 Caricamento")
        f_name = st.file_uploader("Carica NAME.csv", type=['csv'])
        f_data = st.file_uploader("Carica flegrei.csv", type=['csv'])
        st.divider()
        st.header("⚙️ Opzioni Grafico")
        tipo_asse = st.radio("Asse X:", ["Temporale", "Sequenziale (Testo)"])
        passo = st.number_input("Etichette ogni N righe:", 1, 5000, 100)
        st.header("🛡️ Filtri")
        sigma = st.slider("Gauss (Sigma σ)", 0.0, 5.0, 2.5)
        rimuovi_zeri = st.toggle("Rimuovi Zeri Puri", value=True)

    if f_name and f_data:
        # Caricamento: Excel CSV usa spesso ';' o ','
        df_h = pd.read_csv(f_name, sep=None, engine='python', header=None, nrows=3)
        df_v = pd.read_csv(f_data, sep=None, engine='python')

        # 1. Creiamo una mappa tra NOMI NORMALI e NOMI ORIGINALI del file dati
        # Così se nel file dati c'è "CO_9286 VAR8 [蚓]" noi lo troviamo come "CO9286VAR8"
        col_map = {normalize_string(c): c for c in df_v.columns}
        
        # 2. Identifica colonna tempo
        col_t_orig = df_v.columns[0]
        df_v[col_t_orig] = pd.to_datetime(df_v[col_t_orig], errors='coerce')
        df_v = df_v.dropna(subset=[col_t_orig]).sort_values(by=col_t_orig)

        # 3. Parsing Gerarchico
        tree = {}
        for col_idx in range(1, len(df_h.columns)):
            r1 = str(df_h.iloc[0, col_idx]).strip()
            r2 = str(df_h.iloc[1, col_idx]).strip()
            r3_orig = str(df_h.iloc[2, col_idx]).strip()
            
            if r3_orig == "nan" or not r3_orig: continue

            # Normalizziamo r3 per cercarlo nel file dati
            r3_norm = normalize_string(r3_orig)
            
            if r3_norm in col_map:
                cid_reale = col_map[r3_norm]
                centralina = r1 if r1 != "nan" else r3_orig.split()[0]
                sensore = r2 if r2 != "nan" else "Sensore " + r3_orig.split()[0]
                
                if centralina not in tree: tree[centralina] = {}
                if sensore not in tree[centralina]: tree[centralina][sensore] = {}
                
                label = clean_label(r3_orig)
                tree[centralina][sensore][cid_reale] = label

        # --- SELEZIONE UI ---
        c1, c2 = st.columns(2)
        with c1:
            cent_sel = st.selectbox("Seleziona Centralina:", sorted(tree.keys()))
        with c2:
            sens_sel = st.multiselect("Seleziona Sensore/i:", sorted(tree[cent_sel].keys()))

        targets = []
        if sens_sel:
            st.write("---")
            cols = st.columns(len(sens_sel))
            for i, s in enumerate(sens_sel):
                with cols[i]:
                    st.markdown(f"**{s}**")
                    for cid, label in tree[cent_sel][s].items():
                        if st.checkbox(label, key=cid, value=True):
                            targets.append((s, cid, label))

        if targets:
            dr = st.date_input("Periodo:", [df_v[col_t_orig].min().date(), df_v[col_t_orig].max().date()])
            if len(dr) == 2:
                df_p = df_v[(df_v[col_t_orig].dt.date >= dr[0]) & (df_v[col_t_orig].dt.date <= dr[1])].copy().reset_index()

                fig = go.Figure()
                stats_final = {}

                for s_name, cid, label in targets:
                    y_f, diag = applica_filtri_completi(df_p[cid], sigma, rimuovi_zeri)
                    stats_final[f"{s_name} - {label}"] = diag
                    
                    x_axis = df_p.index if tipo_asse == "Sequenziale (Testo)" else df_p[col_t_orig]
                    fig.add_trace(go.Scatter(x=x_axis, y=y_f, name=label, mode='lines+markers'))

                if tipo_asse == "Sequenziale (Testo)":
                    ticks = [df_p.iloc[j][col_t_orig].strftime('%d/%m %H:%M') if j % passo == 0 else "" for j in range(len(df_p))]
                    fig.update_xaxes(tickmode='array', tickvals=list(df_p.index), ticktext=ticks, tickangle=-45)

                fig.update_layout(template="plotly_white", height=600, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

                # Diagnostica
                with st.expander("📝 Analisi Zeri e Gauss"):
                    st.table(pd.DataFrame(stats_final).T)

if __name__ == "__main__":
    main()
