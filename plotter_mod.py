import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import locale
from io import BytesIO

def run_plotter():
    st.header("📉 PLOTTER - Analisi per Grandezza Fisica")
    
    st.sidebar.header("⚙️ Configurazione")
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plotter_final")

    if not file_input:
        st.info("Carica il file Excel per iniziare. Il sistema leggerà il foglio 'NAME' per organizzare i sensori.")
        return

    try:
        xls = pd.ExcelFile(file_input)
        if 'NAME' not in xls.sheet_names:
            st.error("Manca il foglio 'NAME'.")
            return
        
        # 1. Lettura Mappa Sensori (Righe 1, 2, 3)
        df_header = pd.read_excel(file_input, sheet_name='NAME', header=None, nrows=3)
        
        sensor_map = []
        for col in range(1, len(df_header.columns)):
            datalogger = str(df_header.iloc[0, col])
            nome_umano = str(df_header.iloc[1, col])
            info_tech = str(df_header.iloc[2, col]) # ID esatto nel foglio dati
            
            # Estrazione Unità (es. Volt, °C, mm)
            unita = "Altro"
            if "volt" in info_tech.lower() or "[V]" in info_tech.upper(): unita = "Batteria (Volt)"
            elif "°C" in info_tech or "temp" in info_tech.lower(): unita = "Temperatura (°C)"
            elif "mm" in info_tech.lower(): unita = "Spostamento (mm)"
            elif "°" in info_tech: unita = "Inclinazione (°)"
            
            sensor_map.append({
                'id': info_tech,
                'label': f"{nome_umano} ({datalogger})",
                'unita': unita,
                'logger': datalogger
            })

        # 2. Selezione Sequenziale
        st.subheader("1. Seleziona cosa vuoi monitorare")
        unita_disponibili = sorted(list(set([s['unita'] for s in sensor_map])))
        tipo_scelto = st.selectbox("Grandezza Fisica:", unita_disponibili)

        st.subheader(f"2. Seleziona sensori per {tipo_scelto}")
        # Filtriamo i sensori che appartengono solo alla grandezza scelta
        sensori_filtrati = [s for s in sensor_map if s['unita'] == tipo_scelto]
        opzioni = {s['label']: s['id'] for s in sensori_filtrati}
        
        selezione_nomi = st.multiselect("Sensori disponibili:", list(opzioni.keys()))

        if selezione_nomi:
            # Caricamento dati (primo foglio utile)
            data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
            df_data = pd.read_excel(file_input, sheet_name=data_sheet)
            
            # Gestione Date in Italiano
            col_tempo = None
            for c in df_data.columns:
                if 'data' in str(c).lower():
                    col_tempo = c
                    df_data[col_tempo] = pd.to_datetime(df_data[col_tempo])
                    break
            
            # 3. Grafico Plotly
            fig = go.Figure()
            for nome in selezione_nomi:
                id_colonna = opzioni[nome]
                if id_colonna in df_data.columns:
                    fig.add_trace(go.Scatter(
                        x=df_data[col_tempo] if col_tempo else df_data.index,
                        y=df_data[id_colonna],
                        name=nome,
                        mode='lines+markers'
                    ))
            
            fig.update_layout(
                template="plotly_white",
                height=550,
                xaxis_title="Data e Ora",
                yaxis_title=tipo_scelto,
                hovermode="x unified",
                # Formattazione data asse X in stile italiano
                xaxis=dict(tickformat="%d %b %Y\n%H:%M", tickfont=dict(size=10))
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # Export
            csv = df_data[[col_tempo] + [opzioni[n] for n in selezione_nomi]].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica Dati (CSV)", csv, "export_plotter.csv", "text/csv")

    except Exception as e:
        st.error(f"Errore tecnico: {e}")
