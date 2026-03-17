import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from io import BytesIO

# --- OTTIMIZZAZIONE: CARICAMENTO DATI IN CACHE ---
@st.cache_resource
def load_excel_data(file_content):
    xls = pd.ExcelFile(file_content)
    # Carichiamo NAME
    df_header = pd.read_excel(xls, sheet_name='NAME', header=None, nrows=3)
    # Carichiamo il foglio dati (il primo che non è NAME)
    data_sheet_name = [s for s in xls.sheet_names if s != 'NAME'][0]
    df_data = pd.read_excel(xls, sheet_name=data_sheet_name)
    
    # Pulizia colonna tempo
    col_tempo = next((c for c in df_data.columns if 'data' in str(c).lower()), None)
    if col_tempo:
        df_data[col_tempo] = pd.to_datetime(df_data[col_tempo])
        df_data = df_data.sort_values(by=col_tempo)
    
    return df_header, df_data, col_tempo

def run_plotter():
    st.header("📉 PLOTTER - Performance Mode")
    
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plotter_perf")

    if not file_input:
        st.info("In attesa del file Excel...")
        return

    # Caricamento veloce dalla cache
    df_header, df_data, col_tempo = load_excel_data(file_input)

    # 1. Mappatura Sensori
    sensor_map = []
    for col in range(1, len(df_header.columns)):
        info_tech = str(df_header.iloc[2, col])
        unita = "Altro"
        if "volt" in info_tech.lower() or "[V]" in info_tech.upper(): unita = "Batteria (Volt)"
        elif "°C" in info_tech or "temp" in info_tech.lower(): unita = "Temperatura (°C)"
        elif "mm" in info_tech.lower(): unita = "Spostamento (mm)"
        
        sensor_map.append({
            'id': info_tech, 
            'label': f"{df_header.iloc[1, col]} ({df_header.iloc[0, col]})", 
            'unita': unita
        })

    # 2. Selezione Grandezza e Sensori
    c1, c2 = st.columns(2)
    with c1:
        tipo_scelto = st.selectbox("Grandezza:", sorted(list(set([s['unita'] for s in sensor_map]))))
    with c2:
        opzioni = {s['label']: s['id'] for s in sensor_map if s['unita'] == tipo_scelto}
        selezione = st.multiselect("Sensori:", list(opzioni.keys()))

    if selezione and col_tempo:
        # --- GESTIONE DATE ---
        min_d, max_d = df_data[col_tempo].min(), df_data[col_tempo].max()
        
        st.subheader("📅 Intervallo Temporale")
        cd1, cd2 = st.columns(2)
        with cd1:
            start_d = st.date_input("Inizio:", min_d.date(), min_value=min_d.date(), max_value=max_d.date())
        with cd2:
            end_d = st.date_input("Fine:", max_d.date(), min_value=min_d.date(), max_value=max_d.date())

        # Filtraggio immediato in memoria
        mask = (df_data[col_tempo].dt.date >= start_d) & (df_data[col_tempo].dt.date <= end_d)
        df_plot = df_data.loc[mask]

        # 3. GRAFICO REATTIVO
        fig = go.Figure()
        for nome in selezione:
            id_col = opzioni[nome]
            if id_col in df_plot.columns:
                fig.add_trace(go.Scatter(
                    x=df_plot[col_tempo], y=df_plot[id_col],
                    name=nome, mode='lines'
                ))

        fig.update_layout(
            template="plotly_white",
            height=600,
            hovermode="x unified",
            xaxis=dict(
                rangeslider=dict(visible=True),
                type="date",
                tickformat="%d %b %Y",
                # Questo permette al grafico di non ricalcolare tutto ad ogni zoom
                uirevision='constant' 
            ),
            yaxis_title=tipo_scelto
        )

        # Visualizzazione
        st.plotly_chart(fig, use_container_width=True)
        
        # Esportazione rapida
        if st.button("📥 Esporta Excel Filtrato"):
            output = BytesIO()
            df_plot[[col_tempo] + [opzioni[n] for n in selezione]].to_excel(output, index=False)
            st.download_button("Scarica", output.getvalue(), "plot_export.xlsx")
