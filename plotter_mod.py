import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import os

def run_plotter():
    st.header("📈 Analisi Temporale e Grafici")

    # Caricamento file (centrale come richiesto)
    file_input = st.file_uploader("Carica Excel Monitoraggio (es. flegrei.xlsx)", type=['xlsx', 'xlsm'], key="plot_up")

    if not file_input:
        st.info("Carica un file Excel per iniziare l'analisi dei sensori.")
        return

    # Lettura Excel
    xls = pd.ExcelFile(file_input)
    
    # --- GESTIONE ANAGRAFICA (Layer NAME) ---
    mapping_sensori = {}
    if "NAME" in xls.sheet_names:
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        # Riga 1: Datalogger, Riga 2: Nome Sensore, Riga 3: Nome Web
        for col in range(1, df_name.shape[1]):
            dl_nome = str(df_name.iloc[0, col]).strip()
            sens_nome = str(df_name.iloc[1, col]).strip()
            web_nome = str(df_name.iloc[2, col]).strip()
            if web_nome != "nan":
                # Puliamo il nome web per il matching (es. rimuoviamo la grandezza se presente)
                web_base = web_nome.split('[')[0].strip()
                mapping_sensori[web_base] = {
                    "label": f"{sens_nome} ({dl_nome})",
                    "id_umano": sens_nome,
                    "datalogger": dl_nome
                }

    # --- SELEZIONE LAYER DATI ---
    sheets_dati = [s for s in xls.sheet_names if s != "NAME" and s != "ARRAY"]
    sel_sheet = st.selectbox("Seleziona Foglio Dati", sheets_dati)
    
    df = pd.read_excel(xls, sheet_name=sel_sheet)
    if 'Data e Ora' not in df.columns:
        st.error("Colonna 'Data e Ora' non trovata.")
        return

    df['Data e Ora'] = pd.to_datetime(df['Data e Ora'])
    
    # --- ANALISI COLONNE E GRANDEZZE ---
    # Cerchiamo colonne tipo: CO_9277 CL_01_X [°]
    sensor_cols = [c for c in df.columns if '[' in str(c) and ']' in str(c)]
    
    anagrafica_colonne = []
    for col in sensor_cols:
        # Estrazione Grandezza: [mm], [°], [°C], ecc.
        unita = re.search(r'\[(.*?)\]', col).group(0)
        
        # Estrazione Nome Web Base
        # Es: "CO_9277 CL_01_X [°]" -> base: "CO_9277 CL_01"
        # Es: "CO_9286 VAR5 [mm]" -> base: "CO_9286 VAR5"
        nome_web_completo = col.split('[')[0].strip()
        
        # Gestione Multisensore (X, Y, Z, T1...)
        # Se finisce con _X, _Y, _T1 ecc., lo identifichiamo
        sub_param = ""
        parts = nome_web_completo.split('_')
        if parts[-1] in ['X', 'Y', 'Z', 'T1', 'T2', 'LI', 'LQ', 'LM']:
            sub_param = parts[-1]
            base_web = "_".join(parts[:-1]) # Rimuove l'ultimo pezzo (_X)
        else:
            base_web = nome_web_completo

        # Associazione Nome Umano
        info = mapping_sensori.get(base_web, {
            "label": f"{base_web}",
            "id_umano": base_web,
            "datalogger": base_web.split(' ')[0] if ' ' in base_web else "DL_Generico"
        })

        anagrafica_colonne.append({
            "col_originale": col,
            "base_web": base_web,
            "label_umana": info["label"],
            "id_umano": info["id_umano"],
            "parametro": sub_param if sub_param else "Dato",
            "unita": unita
        })

    df_info = pd.DataFrame(anagrafica_colonne)

    # --- UI DI SELEZIONE ---
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. Scegli il Sensore (Nome Umano)
        lista_sensori = df_info["label_umana"].unique()
        sel_sens_label = st.selectbox("Seleziona Sensore", lista_sensori)
    
    with col2:
        # 2. Scegli le Grandezze disponibili per quel sensore
        mask = df_info["label_umana"] == sel_sens_label
        opzioni_grandezze = df_info[mask]
        
        # Creiamo una label per il multiselect: "X [°]", "T1 [°C]" ecc.
        opzioni_grandezze["select_label"] = opzioni_grandezze["parametro"] + " " + opzioni_grandezze["unita"]
        
        sel_params = st.multiselect(
            "Seleziona Grandezze da visualizzare",
            options=opzioni_grandezze["select_label"].tolist(),
            default=opzioni_grandezze["select_label"].tolist()[0]
        )

    # --- GENERAZIONE GRAFICO ---
    if sel_params:
        cols_to_plot = opzioni_grandezze[opzioni_grandezze["select_label"].isin(sel_params)]["col_originale"].tolist()
        
        fig = go.Figure()
        
        for c in cols_to_plot:
            # Recuperiamo l'unità per il titolo asse Y
            u_misura = df_info[df_info["col_originale"] == c]["unita"].values[0]
            nome_traccia = df_info[df_info["col_originale"] == c]["select_label"].values[0]
            
            fig.add_trace(go.Scatter(
                x=df['Data e Ora'],
                y=df[c],
                name=f"{sel_sens_label} - {nome_traccia}",
                mode='lines'
            ))

        fig.update_layout(
            template="plotly_white",
            hovermode="x unified",
            xaxis_title="Tempo",
            yaxis_title=f"Valore ({u_misura})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # Tabella dati per controllo veloce
        with st.expander("Visualizza Tabella Dati"):
            st.dataframe(df[['Data e Ora'] + cols_to_plot].dropna())

# Se eseguito come script principale
if __name__ == "__main__":
    run_plotter()
