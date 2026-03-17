import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import os

# --- GESTIONE LIBRERIA DOCX ---
try:
    from docx import Document
    from docx.shared import Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

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
    st.header("📉 PLOTTER - Debug Mode")
    
    with st.sidebar:
        st.header("⚙️ Impostazioni")
        tipo_asse_x = st.radio("Asse X:", ["Sequenziale (Stile Excel)", "Temporale"])
        passo_date = st.number_input("Etichette ogni N date:", value=400, min_value=1)
        st.divider()
        rimuovi_zeri = st.toggle("Rimuovi Zeri Puri", value=True)
        usa_gauss = st.checkbox("Attiva Gauss", value=True)
        sigma = st.slider("Sigma", 0.5, 5.0, 2.0) if usa_gauss else 0
        
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'])
    if not file_input: return st.info("Carica un file Excel per iniziare.")

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)
        
        # Mappatura
        mappa = {}
        for col in range(1, len(df_header.columns)):
            id_t, nome, logger = str(df_header.iloc[2, col]), str(df_header.iloc[1, col]), str(df_header.iloc[0, col])
            t = "Inclinazione (°)" if "[°]" in id_t else "Temperatura (°C)" if "°C" in id_t else "Spostamento (mm)" if "mm" in id_t.lower() else "Batteria (Volt)" if "[V]" in id_t else "Altro"
            key = f"{nome} ({logger})"
            if key not in mappa: mappa[key] = {"tipo": t, "canali": {}}
            suffix = id_t.split()[-2] if len(id_t.split()) > 2 else id_t
            mappa[key]["canali"][id_t] = suffix

        tipo_sel = st.selectbox("Grandezza:", sorted(list(set([v['tipo'] for v in mappa.values()]))))
        sensori_scelti = st.multiselect("Sensori:", [k for k, v in mappa.items() if v['tipo'] == tipo_sel])

        final_targets = {}
        if sensori_scelti:
            cols = st.columns(len(sensori_scelti))
            for i, s in enumerate(sensori_scelti):
                with cols[i]:
                    assi = st.multiselect(f"Assi {s}:", list(mappa[s]["canali"].keys()), format_func=lambda x: mappa[s]["canali"][x])
                    for a in assi: final_targets[f"{s} - {mappa[s]['canali'][a]}"] = a

        if final_targets:
            d_range = st.date_input("Periodo:", [df_values[col_tempo].min().date(), df_values[col_tempo].max().date()])
            if len(d_range) == 2:
                df_p = df_values[(df_values[col_tempo].dt.date >= d_range[0]) & (df_values[col_tempo].dt.date <= d_range[1])].copy().reset_index(drop=True)
                
                fig = go.Figure()
                stats_final = {}
                
                for label, cid in final_targets.items():
                    if cid in df_p.columns:
                        y_clean, diag = applica_filtri_completi(df_p[cid], sigma, rimuovi_zeri)
                        stats_final[label] = diag
                        
                        # --- FIX ERRORE LENGTH ---
                        # Creiamo un dataframe temporaneo per ogni traccia per garantire stessa lunghezza tra X e Y
                        temp_df = pd.DataFrame({
                            'x_seq': df_p.index,
                            'x_time': df_p[col_tempo],
                            'y': y_clean
                        }).dropna(subset=['y']) # Rimuoviamo i punti filtrati da Gauss/Zeri
                        
                        x_final = temp_df['x_seq'] if "Sequenziale" in tipo_asse_x else temp_df['x_time']
                        
                        fig.add_trace(go.Scatter(
                            x=x_final, 
                            y=temp_df['y'], 
                            name=label, 
                            mode='lines+markers', 
                            connectgaps=True
                        ))

                # Formattazione Asse X
                if "Sequenziale" in tipo_asse_x:
                    ticks_text = [row[col_tempo].strftime('%d/%m/%y %H:%M') if i % passo_date == 0 else "" for i, row in df_p.iterrows()]
                    fig.update_layout(xaxis=dict(type='category', tickmode='array', tickvals=list(df_p.index), ticktext=ticks_text, tickangle=-45))
                
                fig.update_layout(template="plotly_white", height=600, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("📊 Diagnostica Filtri"):
                    st.table(pd.DataFrame(stats_final).T)

    except Exception as e:
        st.error(f"Errore tecnico: {e}")
