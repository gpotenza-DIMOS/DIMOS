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

# --- FUNZIONE PULIZIA STRINGHE ---
def clean_str(s):
    return str(s).strip().replace("  ", " ")

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
        r1 = clean_str(df_header.iloc[0, col_idx])
        r2 = clean_str(df_header.iloc[1, col_idx])
        r3 = clean_str(df_header.iloc[2, col_idx])
        
        if r3 == "nan" or not r3: continue

        parts = r3.split()
        prefix = parts[0]
        
        # Identificazione Centralina
        centralina = r1 if r1 not in ["nan", "", "datalogger"] else prefix
        
        # Identificazione Sensore
        if r2 not in ["nan", ""]:
            sensore = r2
        else:
            if "BATT" in r3: sensore = "Batteria"
            elif "CL_" in r3: sensore = "_".join(r3.split('_')[:3]) # Es: CO_9277_CL_01
            else: sensore = prefix

        if centralina not in tree: tree[centralina] = {}
        if sensore not in tree[centralina]: tree[centralina][sensore] = {}
        
        label_canale = " ".join(parts[1:]) if len(parts) > 1 else r3
        tree[centralina][sensore][r3] = label_canale
    return tree

def main():
    st.set_page_config(layout="wide", page_title="Plotter RFI Pro")
    st.title("📊 Analisi Geotecnica Avanzata")

    with st.sidebar:
        st.header("1. Caricamento")
        f_name = st.file_uploader("File NAME (Metadati)", type=['csv'])
        f_data = st.file_uploader("File DATI", type=['csv'])
        st.divider()
        st.header("2. Analisi e Filtri")
        tipo_asse = st.radio("Asse X:", ["Temporale Reale", "Sequenziale (Testo)"])
        sigma = st.slider("Gauss (Sigma σ)", 0.0, 5.0, 2.5)
        rimuovi_zeri = st.toggle("Rimuovi Zeri", value=True)
        passo_date = st.number_input("Etichette ogni N righe", 1, 1000, 100)

    if f_name and f_data:
        # Caricamento con gestione separatore
        df_h = pd.read_csv(f_name, sep=None, engine='python', header=None, nrows=3)
        df_v = pd.read_csv(f_data, sep=None, engine='python')
        
        # Sincronizzazione nomi colonne per evitare KeyError
        df_v.columns = [clean_str(c) for c in df_v.columns]
        col_t = df_v.columns[0]
        df_v[col_t] = pd.to_datetime(df_v[col_t], errors='coerce')
        df_v = df_v.dropna(subset=[col_t]).sort_values(by=col_t)

        tree = parse_hierarchy(df_h)

        # --- SELEZIONE ---
        c1, c2 = st.columns(2)
        with c1:
            cent_sel = st.selectbox("Seleziona Centralina:", sorted(tree.keys()))
        with c2:
            sens_sel = st.multiselect("Seleziona Sensori:", sorted(tree[cent_sel].keys()))

        targets = []
        if sens_sel:
            st.write("### Canali Disponibili")
            cols = st.columns(len(sens_sel))
            for i, s in enumerate(sens_sel):
                with cols[i]:
                    st.markdown(f"**{s}**")
                    for cid, lab in tree[cent_sel][s].items():
                        # Verifica se il CID esiste davvero nel file dati
                        if cid in df_v.columns:
                            if st.checkbox(lab, key=cid, value=True):
                                targets.append((s, cid, lab))
                        else:
                            st.warning(f"Manca: {cid}")

        if targets:
            # Filtro temporale
            dr = st.date_input("Periodo:", [df_v[col_t].min().date(), df_v[col_t].max().date()])
            if len(dr) == 2:
                df_p = df_v[(df_v[col_t].dt.date >= dr[0]) & (df_v[col_t].dt.date <= dr[1])].copy().reset_index()

                fig = go.Figure()
                stats_final = {}

                for s_name, cid, label in targets:
                    y_f, diag = applica_filtri_completi(df_p[cid], sigma, rimuovi_zeri)
                    tag = f"{s_name} - {label}"
                    stats_final[tag] = diag
                    
                    x_val = df_p.index if tipo_asse == "Sequenziale (Testo)" else df_p[col_t]
                    fig.add_trace(go.Scatter(x=x_val, y=y_f, name=tag, mode='lines+markers'))

                if tipo_asse == "Sequenziale (Testo)":
                    ticks = [df_p.iloc[i][col_t].strftime('%d/%m %H:%M') if i % passo_date == 0 else "" for i in range(len(df_p))]
                    fig.update_xaxes(tickmode='array', tickvals=list(df_p.index), ticktext=ticks, tickangle=-45)

                fig.update_layout(template="plotly_white", height=650, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

                # Diagnostica e Word
                col_res1, col_res2 = st.columns([2, 1])
                with col_res1:
                    with st.expander("📊 Diagnostica Filtri (Zeri e Gauss)"):
                        st.table(pd.DataFrame(stats_final).T)
                with col_res2:
                    st.success("Tutto pronto per il report!")
                    # Qui potresti aggiungere la funzione genera_report_word definita prima

if __name__ == "__main__":
    main()
