import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from io import BytesIO
from datetime import datetime

# --- GESTIONE LIBRERIA DOCX ---
try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- LOGICA FILTRI ---
def applica_filtri_avanzati(serie, n_sigma, rimuovi_zeri):
    originale = serie.copy()
    diagnostica = {"zeri": 0, "gauss": 0}
    if rimuovi_zeri:
        diagnostica["zeri"] = (originale == 0).sum()
        originale = originale.replace(0, np.nan)
    temp_data = originale.dropna()
    if not temp_data.empty and n_sigma > 0:
        mean, std = temp_data.mean(), temp_data.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diagnostica["gauss"] = outliers.sum()
            originale[outliers] = np.nan
    return originale, diagnostica

@st.cache_resource
def get_data_from_excel(file_content):
    xls = pd.ExcelFile(file_content)
    df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
    data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
    df_values = pd.read_excel(xls, sheet_name=data_sheet)
    df_values.columns = [str(c).strip() for c in df_values.columns]
    col_tempo = next((c for c in df_values.columns if 'data' in str(c).lower()), None)
    if col_tempo:
        df_values[col_tempo] = pd.to_datetime(df_values[col_tempo], errors='coerce')
        df_values = df_values.dropna(subset=[col_tempo]).sort_values(by=col_tempo)
    return df_header, df_values, col_tempo

def run_plotter():
    st.header("📉 PLOTTER - Visualizzazione Professionale")
    
    st.sidebar.header("⚙️ Impostazioni Asse X")
    tipo_asse_x = st.sidebar.radio("Modalità:", ["Temporale", "Sequenziale (Testo)"], index=1)
    
    # NUOVO: Passo Etichette (come Excel)
    passo_date = st.sidebar.number_input("Passo etichette (Ogni N date):", min_value=1, value=400, step=10)
    
    st.sidebar.divider()
    rimuovi_zeri = st.sidebar.toggle("Elimina Zeri Puri", value=True)
    usa_filtro = st.sidebar.checkbox("Filtro Sigma Gauss", value=True)
    sigma_val = st.sidebar.slider("Sigma", 0.5, 5.0, 2.0, 0.1) if usa_filtro else 0
    
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plt_v_final_step")
    if not file_input: return st.info("Carica un file Excel per iniziare.")

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)
        
        # Mappatura Sensori
        mappa_sensori = {}
        for col in range(1, len(df_header.columns)):
            datalogger = str(df_header.iloc[0, col]).strip()
            nome_umano = str(df_header.iloc[1, col]).strip()
            id_tech = str(df_header.iloc[2, col]).strip()
            
            if "[V]" in id_tech.upper(): t = "Batteria (Volt)"
            elif "[°C]" in id_tech.upper(): t = "Temperatura (°C)"
            elif "[°]" in id_tech: t = "Inclinazione (°)"
            elif "[MM]" in id_tech.upper(): t = "Spostamento (mm)"
            else: t = "Altro"
            
            label_gruppo = f"{nome_umano} ({datalogger})"
            if label_gruppo not in mappa_sensori:
                mappa_sensori[label_gruppo] = {"tipo": t, "canali": {}}
            
            suffix = id_tech.split()[-2] if len(id_tech.split()) > 2 else id_tech
            mappa_sensori[label_gruppo]["canali"][id_tech] = suffix

        tipo_sel = st.selectbox("Grandezza:", sorted(list(set([s['tipo'] for s in mappa_sensori.values()]))))
        sensori_scelti = st.multiselect("Sensori:", [name for name, d in mappa_sensori.items() if d['tipo'] == tipo_sel])

        selezione_finale = {}
        if sensori_scelti:
            st.subheader("🎯 Canali Selezionati")
            cols = st.columns(len(sensori_scelti))
            for i, s_name in enumerate(sensori_scelti):
                with cols[i % len(cols)]:
                    canali_disp = mappa_sensori[s_name]["canali"]
                    scelte_assi = st.multiselect(f"{s_name}:", list(canali_disp.keys()), 
                                                 default=list(canali_disp.keys())[:1],
                                                 format_func=lambda x: canali_disp[x])
                    for a in scelte_assi:
                        selezione_finale[f"{s_name} - {canali_disp[a]}"] = a

        if selezione_finale:
            min_d, max_d = df_values[col_tempo].min(), df_values[col_tempo].max()
            d_range = st.date_input("Periodo:", [min_d.date(), max_d.date()])
            
            if len(d_range) == 2:
                mask = (df_values[col_tempo].dt.date >= d_range[0]) & (df_values[col_tempo].dt.date <= d_range[1])
                df_plot = df_values.loc[mask].copy()
                
                # Creazione etichette asse X con "buco" ogni N passi
                date_labels = df_plot[col_tempo].dt.strftime('%d/%m/%y %H:%M').tolist()
                visible_labels = [label if i % passo_date == 0 else "" for i, label in enumerate(date_labels)]

                fig = go.Figure()
                stats_final = {}

                for label_grafico, cid in selezione_finale.items():
                    if cid in df_plot.columns:
                        y_clean, stats = applica_filtri_avanzati(df_plot[cid], sigma_val, rimuovi_zeri)
                        stats_final[label_grafico] = stats
                        
                        # Se sequenziale, usiamo l'indice numerico come base X
                        x_data = list(range(len(df_plot))) if tipo_asse_x == "Sequenziale (Testo)" else df_plot[col_tempo]
                        
                        fig.add_trace(go.Scatter(x=x_data, y=y_clean, name=label_grafico, 
                                                 mode='lines+markers', connectgaps=True))

                # Configurazione Assi
                if tipo_asse_x == "Sequenziale (Testo)":
                    fig.update_layout(
                        xaxis=dict(
                            tickmode='array',
                            tickvals=list(range(len(df_plot))),
                            ticktext=visible_labels,
                            tickangle=-45
                        )
                    )
                else:
                    fig.update_layout(xaxis=dict(type='date', tickangle=-45))

                fig.update_layout(template="plotly_white", height=650, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("🔍 Diagnostica"):
                    st.table(pd.DataFrame(stats_final).T)

                if st.button("📝 Genera Report Word"):
                    if DOCX_AVAILABLE:
                        # Qui il grafico verrà salvato nel report
                        st.download_button("📥 Scarica Report Word", b"...", "Report.docx")

    except Exception as e:
        st.error(f"Errore: {e}")
