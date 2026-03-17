import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# (Manteniamo le funzioni di cache e filtro sigma viste in precedenza...)

def run_plotter():
    st.header("📉 PLOTTER - Visualizzazione Stile Excel")
    
    st.sidebar.header("⚙️ Impostazioni Asse X")
    # Questa è la chiave: forziamo l'asse come "Sequenziale" per default
    tipo_asse_x = st.sidebar.selectbox("Tipo Asse X:", ["Sequenziale (Stile Excel)", "Temporale (Reale)"])
    passo_date = st.sidebar.number_input("Intervallo etichette (Ogni N date):", min_value=1, value=400)
    
    # (Resto della configurazione: filtri, file uploader...)
    file_input = st.sidebar.file_uploader("Carica Excel", type=['xlsx', 'xlsm'], key="plt_v_final_excel")
    
    if not file_input:
        return st.info("Carica un file per visualizzare il grafico.")

    try:
        df_header, df_values, col_tempo = get_data_from_excel(file_input)
        
        # ... (Logica di mappatura sensori e selezione canali già vista) ...

        if selezione_finale:
            # Filtro date
            min_d, max_d = df_values[col_tempo].min(), df_values[col_tempo].max()
            d_range = st.date_input("Periodo:", [min_d.date(), max_d.date()])
            
            if len(d_range) == 2:
                mask = (df_values[col_tempo].dt.date >= d_range[0]) & (df_values[col_tempo].dt.date <= d_range[1])
                df_plot = df_values.loc[mask].copy().reset_index(drop=True)

                fig = go.Figure()
                
                # Creiamo le etichette: mostriamo la data solo ogni 'passo_date'
                # Altrimenti lasciamo una stringa vuota ""
                labels_x = []
                for i, row in df_plot.iterrows():
                    if i % passo_date == 0:
                        labels_x.append(row[col_tempo].strftime('%d/%m/%y %H:%M'))
                    else:
                        labels_x.append("")

                for label_grafico, cid in selezione_finale.items():
                    if cid in df_plot.columns:
                        y_clean, _ = applica_filtri_avanzati(df_plot[cid], sigma_val, rimuovi_zeri)
                        
                        if tipo_asse_x == "Sequenziale (Stile Excel)":
                            # Usiamo l'indice numerico (0, 1, 2...) come asse X
                            x_val = df_plot.index 
                        else:
                            x_val = df_plot[col_tempo]

                        fig.add_trace(go.Scatter(
                            x=x_val, 
                            y=y_clean, 
                            name=label_grafico,
                            mode='lines+markers',
                            connectgaps=True,
                            # Hover personalizzato per vedere sempre la data vera anche se nascosta sull'asse
                            hovertemplate="Data: %{customdata}<br>Valore: %{y:.4f}<extra></extra>",
                            customdata=df_plot[col_tempo].dt.strftime('%d/%m/%y %H:%M')
                        ))

                if tipo_asse_x == "Sequenziale (Stile Excel)":
                    fig.update_layout(
                        xaxis=dict(
                            type='category', # Forza il comportamento "Testo" di Excel
                            tickmode='array',
                            tickvals=list(df_plot.index),
                            ticktext=labels_x,
                            tickangle=-45,
                            nticks=20 # Limita il numero totale di etichette visibili per pulizia
                        )
                    )
                else:
                    fig.update_layout(xaxis=dict(type='date'))

                fig.update_layout(
                    template="plotly_white",
                    height=700,
                    margin=dict(l=50, r=50, b=150, t=50), # Più spazio sotto per le date
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Errore: {e}")
