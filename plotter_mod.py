import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from io import BytesIO

# --- CACHE PER VELOCIZZARE IL CARICAMENTO ---
@st.cache_resource
def get_data_from_excel(file_content):
    xls = pd.ExcelFile(file_content)
    # Lettura NAME (prime 3 righe)
    df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
    # Lettura dati (il foglio che non è NAME)
    data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
    df_values = pd.read_excel(xls, sheet_name=data_sheet)
    
    # Pulizia colonna Tempo
    col_tempo = next((c for c in df_values.columns if 'data' in str(c).lower()), None)
    if col_tempo:
        df_values[col_tempo] = pd.to_datetime(df_values[col_tempo])
        df_values = df_values.sort_values(by=col_tempo)
    
    return df_header, df_values, col_tempo

def run_plotter():
    st.header("📉 PLOTTER - Analisi Avanzata")
    
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plotter_v3")

    if not file_input:
        st.info("Carica il file Excel per visualizzare i dati.")
        return

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)

        # 1. MAPPATURA INTELLIGENTE (Logica basata sui tuoi file)
        sensor_map = []
        for col in range(1, len(df_header.columns)):
            datalogger = str(df_header.iloc[0, col])
            nome_umano = str(df_header.iloc[1, col])
            id_tech = str(df_header.iloc[2, col])
            
            # Rilevamento preciso della grandezza
            if "[V]" in id_tech.upper() or "BATT" in id_tech.upper():
                tipo = "Batteria (Volt)"
            elif "[°C]" in id_tech:
                tipo = "Temperatura (°C)"
            elif "[°]" in id_tech:
                tipo = "Inclinazione (°)"
            elif "[mm]" in id_tech.lower():
                tipo = "Spostamento (mm)"
            elif "[UR %]" in id_tech.upper():
                tipo = "Umidità (%)"
            else:
                tipo = "Altro / Generico"
            
            sensor_map.append({'id': id_tech, 'label': f"{nome_umano} ({datalogger})", 'tipo': tipo})

        # 2. INTERFACCIA DI FILTRO
        c1, c2 = st.columns(2)
        with c1:
            tipi_disponibili = sorted(list(set([s['tipo'] for s in sensor_map])))
            tipo_sel = st.selectbox("Cosa vuoi vedere?", tipi_disponibili)
        with c2:
            opzioni = {s['label']: s['id'] for s in sensor_map if s['tipo'] == tipo_sel}
            selezione = st.multiselect("Quali sensori?", list(opzioni.keys()))

        if selezione:
            # FILTRO DATE
            min_date = df_values[col_tempo].min().date()
            max_date = df_values[col_tempo].max().date()
            
            st.write("---")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                d_start = st.date_input("Dal:", min_date)
            with col_d2:
                d_end = st.date_input("Al:", max_date)

            # Filtraggio dataframe
            mask = (df_values[col_tempo].dt.date >= d_start) & (df_values[col_tempo].dt.date <= d_end)
            df_plot = df_values.loc[mask]

            # 3. GRAFICO DINAMICO
            fig = go.Figure()
            for nome in selezione:
                cid = opzioni[nome]
                if cid in df_plot.columns:
                    fig.add_trace(go.Scatter(
                        x=df_plot[col_tempo], y=df_plot[cid],
                        name=nome, mode='lines',
                        hovertemplate=f"%{{y:.3f}} {tipo_sel}<br>%{{x}}"
                    ))
                else:
                    st.warning(f"Colonna non trovata nei dati: {cid}")

            fig.update_layout(
                template="plotly_white",
                height=600,
                xaxis=dict(
                    rangeslider=dict(visible=True), 
                    tickformat="%d %b %y\n%H:%M",
                    uirevision='constant' # Mantiene lo zoom attivo
                ),
                yaxis_title=tipo_sel,
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # EXPORT
            if st.button("📥 Esporta questa selezione"):
                output = BytesIO()
                df_plot[[col_tempo] + [opzioni[n] for n in selezione]].to_excel(output, index=False)
                st.download_button("Scarica Excel", output.getvalue(), "plotter_export.xlsx")

    except Exception as e:
        st.error(f"Errore: {e}")
