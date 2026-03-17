import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from io import BytesIO

@st.cache_resource
def get_data_from_excel(file_content):
    xls = pd.ExcelFile(file_content)
    df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
    data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
    df_values = pd.read_excel(xls, sheet_name=data_sheet)
    
    # Pulizia nomi colonne dati: rimuoviamo spazi bianchi extra all'inizio/fine
    df_values.columns = [str(c).strip() for c in df_values.columns]
    
    col_tempo = next((c for c in df_values.columns if 'data' in str(c).lower()), None)
    if col_tempo:
        df_values[col_tempo] = pd.to_datetime(df_values[col_tempo], errors='coerce')
        df_values = df_values.dropna(subset=[col_tempo]).sort_values(by=col_tempo)
    
    return df_header, df_values, col_tempo

def run_plotter():
    st.header("📉 PLOTTER - Diagnostica e Visualizzazione")
    
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plotter_v4")

    if not file_input:
        st.info("Carica il file Excel per iniziare.")
        return

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)

        # 1. MAPPATURA E PULIZIA ID
        sensor_map = []
        for col in range(1, len(df_header.columns)):
            datalogger = str(df_header.iloc[0, col]).strip()
            nome_umano = str(df_header.iloc[1, col]).strip()
            id_tech = str(df_header.iloc[2, col]).strip() # Pulizia ID tecnico
            
            if "[V]" in id_tech.upper(): tipo = "Batteria (Volt)"
            elif "[°C]" in id_tech.upper(): tipo = "Temperatura (°C)"
            elif "[°]" in id_tech: tipo = "Inclinazione (°)"
            elif "[MM]" in id_tech.upper(): tipo = "Spostamento (mm)"
            elif "[UR %]" in id_tech.upper(): tipo = "Umidità (%)"
            else: tipo = "Altro"
            
            sensor_map.append({'id': id_tech, 'label': f"{nome_umano} ({datalogger})", 'tipo': tipo})

        # 2. INTERFACCIA
        tipi_disponibili = sorted(list(set([s['tipo'] for s in sensor_map])))
        tipo_sel = st.selectbox("Seleziona Grandezza:", tipi_disponibili)
        
        opzioni = {s['label']: s['id'] for s in sensor_map if s['tipo'] == tipo_sel}
        selezione = st.multiselect("Seleziona Sensori:", list(opzioni.keys()))

        if selezione:
            # FILTRO TEMPORALE
            min_date, max_date = df_values[col_tempo].min(), df_values[col_tempo].max()
            d_range = st.date_input("Intervallo temporale:", [min_date.date(), max_date.date()])
            
            if len(d_range) == 2:
                mask = (df_values[col_tempo].dt.date >= d_range[0]) & (df_values[col_tempo].dt.date <= d_range[1])
                df_plot = df_values.loc[mask]

                fig = go.Figure()
                for nome in selezione:
                    cid = opzioni[nome]
                    
                    if cid in df_plot.columns:
                        # Rimuoviamo i NaN solo per questa traccia per non interrompere la linea
                        trace_data = df_plot[[col_tempo, cid]].dropna()
                        
                        fig.add_trace(go.Scatter(
                            x=trace_data[col_tempo], 
                            y=trace_data[cid],
                            name=nome, 
                            mode='lines+markers',
                            connectgaps=True, # UNISCE I PUNTI ANCHE SE MANCANO DATI
                            hovertemplate=f"%{{y:.3f}} {tipo_sel}<br>%{{x}}"
                        ))
                    else:
                        st.error(f"Non trovo la colonna: '{cid}' nel foglio dati.")
                
                fig.update_layout(
                    template="plotly_white", height=600,
                    xaxis=dict(rangeslider=dict(visible=True), tickformat="%d %b %y\n%H:%M"),
                    yaxis_title=tipo_sel, hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"Si è verificato un errore: {e}")
