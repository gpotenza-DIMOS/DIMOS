import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from io import BytesIO

def run_plotter():
    st.header("📉 PLOTTER - Analisi Multi-Sensore")
    
    st.sidebar.header("⚙️ Configurazione Plotter")
    file_input = st.sidebar.file_uploader("Carica Excel Monitoraggio", type=['xlsx', 'xlsm'], key="plotter_upload")

    if not file_input:
        st.info("Carica il file Excel per visualizzare i sensori disponibili (Foglio NAME richiesto).")
        return

    try:
        # Lettura del file Excel
        xls = pd.ExcelFile(file_input)
        
        if 'NAME' not in xls.sheet_names:
            st.error("Errore: Il foglio 'NAME' non esiste in questo file.")
            return
        
        # 1. Analisi Struttura Intestazioni dal foglio NAME (Righe 1, 2, 3)
        # Leggiamo le prime 3 righe (header=None per gestire i dati grezzi)
        df_header = pd.read_excel(file_input, sheet_name='NAME', header=None, nrows=3)
        
        sensor_map = []
        # Cicliamo sulle colonne (saltando la prima che solitamente è la data o etichetta)
        for col in range(1, len(df_header.columns)):
            datalogger = str(df_header.iloc[0, col]) # Riga 1
            nome_umano = str(df_header.iloc[1, col]) # Riga 2
            info_raw = str(df_header.iloc[2, col])   # Riga 3 (ID informatico + unità)
            
            # Estrazione unità di misura (cerca tra parentesi quadre o tonde)
            unita = "Generico"
            match = re.search(r'[\[\(](.*?)[\]\)]', info_raw)
            if match:
                unita = match.group(1)
            elif "°C" in info_raw: unita = "°C"
            elif "mm" in info_raw: unita = "mm"
            elif "Volt" in info_raw or " V " in info_raw: unita = "Volt"
                
            sensor_map.append({
                'id_tech': info_raw,
                'label': f"{nome_umano} [{unita}] ({datalogger})",
                'datalogger': datalogger,
                'unita': unita
            })

        # 2. Interfaccia di Selezione e Filtri
        st.subheader("Filtri e Selezione Sensori")
        
        c1, c2 = st.columns(2)
        with c1:
            all_units = sorted(list(set([s['unita'] for s in sensor_map])))
            tipo_sel = st.multiselect("Filtra per Grandezza:", all_units, default=all_units)
        with c2:
            all_loggers = sorted(list(set([s['datalogger'] for s in sensor_map])))
            logger_sel = st.multiselect("Filtra per Datalogger:", all_loggers, default=all_loggers)

        # Filtriamo la lista in base ai criteri scelti
        sensori_filtrati = [s for s in sensor_map if s['unita'] in tipo_sel and s['datalogger'] in logger_sel]
        opzioni_finali = {s['label']: s for s in sensori_filtrati}
        
        selezione = st.multiselect("Scegli i sensori da plottare:", list(opzioni_finali.keys()))

        if selezione:
            # Carichiamo i dati (il primo foglio che non è NAME)
            data_sheet_name = [s for s in xls.sheet_names if s != 'NAME'][0]
            df_data = pd.read_excel(file_input, sheet_name=data_sheet_name)
            
            # Cerchiamo la colonna temporale
            time_col = None
            for col in df_data.columns:
                if 'data' in str(col).lower() or 'ora' in str(col).lower():
                    time_col = col
                    df_data[time_col] = pd.to_datetime(df_data[time_col])
                    break
            
            x_axis = df_data[time_col] if time_col else df_data.index

            # 3. Creazione del Grafico
            fig = go.Figure()
            
            for nome_sel in selezione:
                s_info = opzioni_finali[nome_sel]
                col_id = s_info['id_tech']
                
                if col_id in df_data.columns:
                    fig.add_trace(go.Scatter(
                        x=x_axis, 
                        y=df_data[col_id],
                        name=nome_sel,
                        mode='lines',
                        hovertemplate=f"Valore: %{{y:.2f}} {s_info['unita']}<br>Data: %{{x}}"
                    ))
                else:
                    st.warning(f"Dati non trovati per la colonna: {col_id}")

            fig.update_layout(
                template="plotly_white",
                hovermode="x unified",
                xaxis_title="Tempo",
                yaxis_title="Valore Misurato",
                height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # 4. Esportazione
            if st.button("📊 Prepara Export Excel"):
                cols_to_export = ([time_col] if time_col else []) + [opzioni_finali[n]['id_tech'] for n in selezione]
                df_export = df_data[cols_to_export]
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, index=False, sheet_name='Dati_Plotter')
                
                st.download_button(
                    label="📥 Scarica Excel Dati Selezionati",
                    data=output.getvalue(),
                    file_name="export_plotter.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Si è verificato un errore: {e}")
