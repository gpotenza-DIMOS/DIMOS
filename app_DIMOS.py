import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    DOC_OK = True
except:
    DOC_OK = False

# --- CONFIGURAZIONE PAGINA (UNICA) ---
st.set_page_config(page_title="DIMOS - Monitoraggio Avanzato", layout="wide")

# --- ASSETS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_path(f): return os.path.join(BASE_DIR, f)

# --- LOGIN ---
def check_password():
    if "auth" not in st.session_state: st.session_state["auth"] = False
    if st.session_state["auth"]: return True
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists(get_path("logo_dimos.jpg")):
            st.image(get_path("logo_dimos.jpg"), width=400)
        st.markdown("<h2 style='text-align: center;'>Accesso Sistema DIMOS</h2>", unsafe_allow_html=True)
        u = st.text_input("Utente")
        p = st.text_input("Password", type="password")
        if st.button("Entra"):
            if u == "dimos" and p == "micai!":
                st.session_state["auth"] = True
                st.rerun()
            else: st.error("Credenziali errate")
    return False

# --- MOTORE DI CALCOLO ELETTROLIVELLE (VBA STYLE) ---
def elabora_elettrolivelle(df_values, l_barra, n_sigma, drop_zeros):
    if drop_zeros:
        df_values = df_values.replace(0, np.nan)
    
    # Conversione angoli (°) -> spostamento (mm)
    data_mm = l_barra * np.sin(np.radians(df_values.values))
    # Calcolo variazione rispetto allo zero (C0)
    data_c0 = data_mm - data_mm[0, :]
    
    # Filtro Gauss
    data_proc = data_c0.copy()
    if n_sigma > 0:
        means = np.nanmean(data_proc, axis=0)
        stds = np.nanstd(data_proc, axis=0)
        for j in range(data_proc.shape[1]):
            m, s = means[j], stds[j]
            if s > 0:
                mask = (data_proc[:, j] < m - n_sigma*s) | (data_proc[:, j] > m + n_sigma*s)
                data_proc[mask, j] = m
    return pd.DataFrame(data_proc, index=df_values.index, columns=df_values.columns)

# --- ESECUZIONE ---
if check_password():
    # Stile Sidebar
    st.markdown("<style>[data-testid='stSidebar'] {background-color: #B3CEE5;}</style>", unsafe_allow_html=True)

    # Logo Principale e Titolo
    if os.path.exists(get_path("logo_dimos.jpg")): 
        st.image(get_path("logo_dimos.jpg"), width=400)
    st.markdown("# Dati Monitoraggio - Visualizzazione e stampa")

    with st.sidebar:
        if os.path.exists(get_path("logo_microgeo.jpg")):
            st.image(get_path("logo_microgeo.jpg"), use_container_width=True)
        st.header("⚙️ Parametri Analisi")
        l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
        sigma_val = st.slider("Filtro Gauss (Sigma)", 1.0, 5.0, 3.0, 0.1)
        rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
        vel_vid = st.slider("Velocità Animazione (ms)", 50, 1000, 200)
        if st.button("Logout"):
            st.session_state["auth"] = False
            st.rerun()

    file_in = st.file_uploader("📂 Carica Excel", type=['xlsx', 'xlsm'])

    if file_in:
        xls = pd.ExcelFile(file_in)
        # Identificazione fogli
        sheet_dati = [s for s in xls.sheet_names if s != "NAME" and not s.endswith(("C0", "C", "CP0"))][0]
        df_full = pd.read_excel(xls, sheet_name=sheet_dati)
        
        # Gestione Tempo
        col_t = df_full.columns[0]
        df_full[col_t] = pd.to_datetime(df_full[col_t], dayfirst=True)
        
        # Parsing Gerarchia (NAME)
        gerarchia = {}
        if "NAME" in xls.sheet_names:
            df_n = pd.read_excel(xls, sheet_name="NAME", header=None)
            for i in range(1, len(df_full.columns)):
                try:
                    dl = str(df_n.iloc[0, i]).strip()
                    sens = str(df_n.iloc[1, i]).strip()
                except:
                    c = df_full.columns[i]
                    dl = c.split('_')[0] + "_" + c.split('_')[1] if '_' in c else c
                    sens = c
                if dl not in gerarchia: gerarchia[dl] = {}
                if sens not in gerarchia[dl]: gerarchia[dl][sens] = []
                gerarchia[dl][sens].append(df_full.columns[i])

        # Selezione UI
        st.subheader("🔍 Selezione Dati")
        c1, c2 = st.columns(2)
        with c1: sel_dls = st.multiselect("Centraline", sorted(gerarchia.keys()))
        with c2:
            s_list = []
            for d in sel_dls: s_list.extend(gerarchia[d].keys())
            sel_sens = st.multiselect("Sensori", sorted(list(set(s_list))))

        tab1, tab2 = st.tabs(["📊 Analisi Dinamica", "🖨️ Export & Report"])

        with tab1:
            # Filtro temporale
            st.write("**Intervallo Temporale**")
            t_min, t_max = df_full[col_t].min(), df_full[col_t].max()
            d1, d2 = st.columns(2)
            start_d = d1.date_input("Dal", t_min)
            end_d = d2.date_input("Al", t_max)
            
            mask = (df_full[col_t].dt.date >= start_d) & (df_full[col_t].dt.date <= end_d)
            df_f = df_full.loc[mask]

            # Elaborazione Colonne
            cols_to_plot = []
            for d in sel_dls:
                for s in sel_sens:
                    if s in gerarchia[d]: cols_to_plot.extend(gerarchia[d][s])

            if cols_to_plot:
                # Se sono Elettrolivelle (CL), applichiamo trasformazione VBA
                is_cl = any("CL_" in c for c in cols_to_plot)
                
                if is_cl:
                    df_proc = elabora_elettrolivelle(df_f[cols_to_plot], l_barra, sigma_val, rimuovi_zeri)
                else:
                    df_proc = df_f[cols_to_plot] # Altri sensori (BATT, ecc)

                # GRAFICO TREND
                fig = go.Figure()
                for c in cols_to_plot:
                    fig.add_trace(go.Scatter(x=df_f[col_t], y=df_proc[c], name=c))
                
                fig.update_layout(height=500, xaxis=dict(rangeslider=dict(visible=True)), template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

                # SEZIONE ANIMAZIONE (Se elettrolivelle)
                if is_cl:
                    st.divider()
                    st.subheader("🎬 Animazione Deformata")
                    cl_labels = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in cols_to_plot]
                    
                    fig_anim = go.Figure(
                        data=[go.Scatter(x=cl_labels, y=df_proc.iloc[0], mode='lines+markers+text', 
                                         textposition="top center", marker=dict(size=12, color='blue'))],
                        layout=go.Layout(
                            xaxis=dict(type='category', title="ID Sensore"),
                            yaxis=dict(title="Spostamento (mm)"),
                            updatemenus=[dict(type="buttons", buttons=[dict(label="Play", method="animate", args=[None])])]
                        ),
                        frames=[go.Frame(data=[go.Scatter(x=cl_labels, y=df_proc.iloc[i])], name=str(i)) 
                                for i in range(len(df_proc))]
                    )
                    st.plotly_chart(fig_anim, use_container_width=True)

        with tab2:
            st.subheader("Esportazione")
            # Pulsanti Word/Excel come nel tuo originale...
            if st.button("💾 Scarica Ascisse (TXT)"):
                txt = df_f[col_t].dt.strftime('%d/%m/%Y %H:%M:%S').to_string(index=False)
                st.download_button("Download TXT", txt, "ascisse.txt")
