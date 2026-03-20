import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re
import os
from io import BytesIO
from datetime import datetime

# --- FUNZIONE COLORE VBA ---
def get_vba_color(val):
    v = abs(val)
    if pd.isna(v): return "gray"
    if v <= 1: return "rgb(146, 208, 80)"
    if v <= 2: return "rgb(0, 176, 80)"
    if v <= 3: return "rgb(255, 255, 0)"
    if v <= 4: return "rgb(255, 192, 0)"
    if v <= 5: return "rgb(255, 0, 0)"
    return "rgb(112, 48, 160)"

def run_elettrolivelle():
    st.title("📏 Analisi Elettrolivelle (Sequenza ARRAY)")
    
    up = st.file_uploader("Carica il file Excel", type=['xlsm', 'xlsx'])
    
    if up:
        xls = pd.ExcelFile(up)
        
        # 1. CARICAMENTO SEQUENZA DA FOGLIO ARRAY
        if "ARRAY" not in xls.sheet_names:
            st.error("Manca il foglio 'ARRAY'")
            return
        
        # Leggiamo ARRAY: la colonna 0 è il nome linea, le altre sono i sensori
        df_array = pd.read_excel(xls, "ARRAY", header=None)
        linee_nomi = df_array[0].dropna().unique().tolist()
        sel_linea = st.selectbox("Seleziona Linea", linee_nomi)
        
        # Otteniamo la lista ordinata dei sensori per la linea scelta
        riga_linea = df_array[df_array[0] == sel_linea].iloc[0, 1:]
        sequenza_ordinata = riga_linea.dropna().astype(str).tolist()
        
        st.info(f"Sequenza rilevata: {' -> '.join(sequenza_ordinata)}")

        # 2. PARAMETRI SIDEBAR
        with st.sidebar:
            asse = st.selectbox("Asse", ["X", "Y"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma_val = st.slider("Gauss Sigma", 1.0, 4.0, 2.0)
            limite_y = st.number_input("Scala Y (+/- mm)", value=20.0)

        # 3. RICERCA DATI NEI FOGLI ETS
        df_dati = None
        for s_name in ["ETS_1", "ETS_2", "ETS_3", "ETS_4"]:
            if s_name in xls.sheet_names:
                temp_df = pd.read_excel(xls, s_name)
                # Se trovo almeno un sensore della sequenza in questo foglio, lo prendo
                if any(str(s) in "".join(temp_df.columns.astype(str)) for s in sequenza_ordinata):
                    df_dati = temp_df
                    break
        
        if df_dati is not None:
            time_col = pd.to_datetime(df_dati.iloc[:, 0])
            
            # --- MAPPATURA COLONNE RISPETTO ALLA SEQUENZA ARRAY ---
            cols_per_grafico = []
            labels_esistenti = []
            
            for s_id in sequenza_ordinata:
                # Cerca la colonna che contiene l'ID del sensore E l'asse scelto
                regex = re.compile(rf".*{s_id}.*_{asse}", re.IGNORECASE)
                match = [c for c in df_dati.columns if regex.search(str(c))]
                
                if match:
                    cols_per_grafico.append(match[0])
                    labels_esistenti.append(s_id)
                else:
                    # Se un sensore di ARRAY non è nel foglio dati, mettiamo un segnaposto
                    # Questo garantisce che la sequenza X non si "rompa"
                    cols_per_grafico.append(None)
                    labels_esistenti.append(f"{s_id} (N.D.)")

            # Estrazione valori
            values_list = []
            for col in cols_per_grafico:
                if col:
                    # Calcolo mm (Sin * L)
                    v_raw = df_dati[col].replace(0, np.nan)
                    v_mm = l_barra * np.sin(np.radians(v_raw))
                    # Calcolo C0 (Delta rispetto alla prima riga)
                    v_c0 = v_mm - v_mm.iloc[0]
                    values_list.append(v_c0)
                else:
                    values_list.append(pd.Series([np.nan] * len(df_dati)))

            df_elaborato = pd.concat(values_list, axis=1)
            
            # Filtro Gauss su tutto il dataframe
            m_vec = df_elaborato.mean()
            s_vec = df_elaborato.std()
            df_elaborato = df_elaborato.mask(np.abs(df_elaborato - m_vec) > (s_vec * sigma_val))
            # Filtro Soglie
            df_elaborato = df_elaborato.mask((df_elaborato > 20) | (df_elaborato < -30))

            # --- GRAFICO PLOTLY ---
            idx = st.slider("Seleziona Istante Temporale", 0, len(time_col)-1, len(time_col)-1)
            
            current_row = df_elaborato.iloc[idx].values
            current_colors = [get_vba_color(v) for v in current_row]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=labels_esistenti, 
                y=current_row,
                mode='lines+markers+text',
                text=[f"{v:.2f}" if pd.notnull(v) else "" for v in current_row],
                textposition="top center",
                marker=dict(size=12, color=current_colors, line=dict(width=1, color="black")),
                line=dict(color="rgba(100,100,100,0.5)", width=2)
            ))
            
            fig.update_layout(
                title=f"Analisi Linea: {sel_linea} | Data: {time_col[idx]}",
                yaxis=dict(range=[-limite_y, limite_y], title="Spostamento (mm)"),
                xaxis=dict(title="Sequenza Sensori (da foglio ARRAY)", type='category'),
                template="plotly_white", 
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error("Dati non trovati per i sensori specificati in ARRAY.")
