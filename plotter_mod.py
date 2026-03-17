import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from io import BytesIO

def run_plotter():
    st.header("📉 PLOTTER - Analisi Multi-Sensore")
    
    st.sidebar.header("⚙️ Configurazione")
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plotter_time")

    if not file_input:
        st.info("Carica il file Excel per iniziare. Il sistema utilizzerà il foglio 'NAME' per i sensori.")
        return

    try:
        xls = pd.ExcelFile(file_input)
        if 'NAME' not in xls.sheet_names:
            st.error("Manca il foglio 'NAME'.")
            return
        
        # 1. Mappatura Sensori dal foglio NAME
        df_header = pd.read_excel(file_input, sheet_name='NAME', header=None, nrows=3)
        sensor_map = []
        for col in range(1, len(df_header.columns)):
            datalogger = str(df_header.iloc[0, col])
            nome_umano = str(df_header.iloc[1, col])
            info_tech = str(df_header.iloc[2, col])
            
            unita = "Altro"
            if "volt" in info_tech.lower() or "[V]" in info_tech.upper(): unita = "Batteria (Volt)"
            elif "°C" in info_tech or "temp" in info_tech.lower(): unita = "Temperatura (°C)"
            elif "mm" in info_tech.lower(): unita = "Spostamento (mm)"
            elif "°" in info_tech: unita = "Inclinazione (°)"
            
            sensor_map.append({'id': info_tech, 'label': f"{nome_umano} ({datalogger})", 'unita': unita})

        # 2. Selezione Grandezza e Sensori
        col_a, col_b = st.columns(2)
        with col_a:
            unita_disponibili = sorted(list(set([s['unita'] for s in sensor_map])))
            tipo_scelto = st.selectbox("Seleziona Grandezza:", unita_disponibili)
        with col_b:
            sensori_filtrati = [s for s in sensor_map if s['unita'] == tipo_scelto]
            opzioni = {s['label']: s['id'] for s in sensori_filtrati}
            selezione_nomi = st.multiselect("Seleziona Sensori:", list(opzioni.keys()))

        if selezione_nomi:
            # Caricamento Dati
            data_sheet = [s for s in xls.sheet_names if s != 'NAME'][0]
            df_data = pd.read_excel(file_input, sheet_name=data_sheet)
            
            # Identificazione Colonna Tempo
            col_tempo = next((c for c in df_data.columns if 'data' in str(c).lower()), None)
            if col_tempo:
                df_data[col_tempo] = pd.to_datetime(df_data[col_tempo])
                df_data = df_data.sort_values(by=col_tempo)
                
                # --- FILTRO TEMPORALE DINAMICO (Calendario) ---
                st.subheader("📅 Filtro Arco Temporale")
                min_date = df_data[col_tempo].min().date()
                max_date = df_data[col_tempo].max().date()
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    start_date = st.date_input("Data Inizio:", min_date, min_value=min_date, max_value=max_date)
                with col_d2:
                    end_date = st.date_input("Data Fine:", max_date, min_value=min_date, max_value=max_date)
                
                # Filtraggio dataframe
                mask = (df_data[col_tempo].dt.date >= start_date) & (df_data[col_tempo].dt.date <= end_date)
                df_filtered = df_data.loc[mask]
            else:
                df_filtered = df_data
                st.warning("Colonna temporale non trovata. Uso indici numerici.")

            # 3. Grafico con Cursore (Rangeslider)
            fig = go.Figure()
            for nome in selezione_nomi:
                id_col = opzioni[nome]
                if id_col in df_filtered.columns:
                    fig.add_trace(go.Scatter(
                        x=df_filtered[col_tempo] if col_tempo else df_filtered.index,
                        y=df_filtered[id_col],
                        name=nome,
                        mode='lines+markers'
                    ))

            fig.update_layout(
                template="plotly_white",
                height=600,
                xaxis_title="Data e Ora (Italiano)",
                yaxis_title=tipo_scelto,
                hovermode="x unified",
                # Configurazione Cursore Dinamico e Formato Italiano
                xaxis=dict(
                    rangeslider=dict(visible=True), # IL CURSORE
                    type="date",
                    tickformat="%d %b %Y\n%H:%M",
                    tickfont=dict(size=10),
                    # Traduzione abbreviata mesi (Plotly usa standard JS, %b adatta al sistema)
                )
            )
            
            # Imposta lingua italiana per i testi di Plotly (se supportato dal browser)
            fig.update_xaxes(rangeselector_font_size=12)
            
            st.plotly_chart(fig, use_container_width=True)

            # Export
            if st.button("📥 Esporta questa vista in Excel"):
                output = BytesIO()
                df_filtered[[col_tempo] + [opzioni[n] for n in selezione_nomi]].to_excel(output, index=False)
                st.download_button("Scarica file", output.getvalue(), "plotter_personalizzato.xlsx")

    except Exception as e:
        st.error(f"Errore tecnico: {e}")
