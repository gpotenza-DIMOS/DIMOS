import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
from io import BytesIO

# --- CARICAMENTO E CACHE ---
@st.cache_resource
def get_data_from_excel(file_content):
    xls = pd.ExcelFile(file_content)
    df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
    data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
    df_values = pd.read_excel(xls, sheet_name=data_sheet)
    
    # Pulizia nomi colonne
    df_values.columns = [str(c).strip() for c in df_values.columns]
    col_tempo = next((c for c in df_values.columns if 'data' in str(c).lower()), None)
    
    if col_tempo:
        df_values[col_tempo] = pd.to_datetime(df_values[col_tempo], errors='coerce')
        df_values = df_values.dropna(subset=[col_tempo]).sort_values(by=col_tempo)
    
    return df_header, df_values, col_tempo

# --- FILTRO SIGMA GAUSS ---
def applica_filtro_sigma(serie, n_sigma):
    data = serie.copy()
    # Rimuoviamo gli zeri puri (spesso errori di lettura) prima del calcolo statistico
    data = data.replace(0, np.nan)
    
    mean = data.mean()
    std = data.std()
    if std == 0 or pd.isna(std): return data
    
    lower_bound = mean - n_sigma * std
    upper_bound = mean + n_sigma * std
    
    # Filtriamo gli outlyer
    data[(data < lower_bound) | (data > upper_bound)] = np.nan
    return data

def run_plotter():
    st.header("📉 PLOTTER - Analisi Dati e Diagnostica")
    
    # Sidebar Parametri
    st.sidebar.header("⚙️ Parametri Analisi")
    rimuovi_zeri = st.sidebar.toggle("Elimina Zeri Puri (0.0)", value=True)
    usa_filtro = st.sidebar.checkbox("Attiva Filtro Sigma Gauss", value=True)
    sigma_val = st.sidebar.slider("Sensibilità Sigma", 0.5, 5.0, 2.0, step=0.1)
    
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plotter_v6")

    if not file_input:
        st.info("Carica il file Excel per iniziare.")
        return

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)

        # 1. MAPPATURA SENSORI
        sensor_map = []
        for col in range(1, len(df_header.columns)):
            id_tech = str(df_header.iloc[2, col]).strip()
            label = f"{str(df_header.iloc[1, col]).strip()} ({str(df_header.iloc[0, col]).strip()})"
            
            # Categorizzazione
            if "[V]" in id_tech.upper(): tipo = "Batteria (Volt)"
            elif "[°C]" in id_tech.upper(): tipo = "Temperatura (°C)"
            elif "[°]" in id_tech: tipo = "Inclinazione (°)"
            elif "[MM]" in id_tech.upper(): tipo = "Spostamento (mm)"
            elif "[UR %]" in id_tech.upper(): tipo = "Umidità (%)"
            else: tipo = "Altro"
            
            sensor_map.append({'id': id_tech, 'label': label, 'tipo': tipo})

        # 2. SELEZIONE
        tipi_disponibili = sorted(list(set([s['tipo'] for s in sensor_map])))
        tipo_sel = st.selectbox("Seleziona Grandezza Fisica:", tipi_disponibili)
        
        opzioni = {s['label']: s['id'] for s in sensor_map if s['tipo'] == tipo_sel}
        selezione = st.multiselect("Seleziona Sensori:", list(opzioni.keys()))

        if selezione:
            # FILTRO TEMPORALE
            min_date, max_date = df_values[col_tempo].min(), df_values[col_tempo].max()
            d_range = st.date_input("Intervallo temporale:", [min_date.date(), max_date.date()])
            
            if len(d_range) == 2:
                mask = (df_values[col_tempo].dt.date >= d_range[0]) & (df_values[col_tempo].dt.date <= d_range[1])
                df_plot = df_values.loc[mask].copy()

                fig = go.Figure()
                for nome in selezione:
                    cid = opzioni[nome]
                    
                    if cid in df_plot.columns:
                        y_data = df_plot[cid].copy()
                        
                        # Step 1: Rimozione Zeri
                        if rimuovi_zeri:
                            y_data = y_data.replace(0, np.nan)
                        
                        # Step 2: Filtro Gauss
                        if usa_filtro:
                            y_data = applica_filtro_sigma(y_data, sigma_val)
                        
                        # Creazione dataset pulito per il plot
                        trace_df = pd.DataFrame({'x': df_plot[col_tempo], 'y': y_data}).dropna()
                        
                        fig.add_trace(go.Scatter(
                            x=trace_df['x'], 
                            y=trace_df['y'],
                            name=nome, 
                            mode='lines+markers',
                            connectgaps=True,
                            hovertemplate=f"%{{y:.4f}} {tipo_sel}<br>%{{x}}"
                        ))
                    else:
                        st.warning(f"Colonna '{cid}' non trovata.")
                
                fig.update_layout(
                    template="plotly_white", height=650,
                    xaxis=dict(rangeslider=dict(visible=True), tickformat="%d %b %y\n%H:%M"),
                    yaxis_title=f"{tipo_sel} {'(Filtrato)' if usa_filtro else ''}",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Feedback sullo stato dei filtri
                c_info1, c_info2 = st.columns(2)
                with c_info1:
                    if rimuovi_zeri: st.success("✅ Zeri puri rimossi")
                with c_info2:
                    if usa_filtro: st.info(f"ℹ️ Filtro Gauss attivo (±{sigma_val} σ)")

    except Exception as e:
        st.error(f"Errore: {e}")
