import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats

# Configurazione Pagina
st.set_page_config(page_title="DIMOS - Analisi Topografica", layout="wide")

def applica_filtro_sigma(df, colonna, n_sigma):
    """Rimuove i dati che superano il numero di Sigma impostato"""
    media = df[colonna].mean()
    std = df[colonna].std()
    limite_inf = media - n_sigma * std
    limite_sup = media + n_sigma * std
    return df[(df[colonna] >= limite_inf) & (df[colonna] <= limite_sup)]

def main():
    st.sidebar.title("Configurazione Report")
    
    # 1. UPLOAD FILE
    uploaded_file = st.sidebar.file_uploader("Carica export Excel/CSV", type=["xlsx", "csv"])

    if uploaded_file:
        # Caricamento dinamico dei fogli (Punti)
        xl = pd.ExcelFile(uploaded_file)
        fogli_disponibili = xl.sheet_names
        
        # 2. SELEZIONE PUNTI (Checkbox/Multiselect)
        st.sidebar.subheader("Selezione Punti")
        seleziona_tutti = st.sidebar.checkbox("Seleziona tutti i punti")
        
        if seleziona_tutti:
            punti_scelti = fogli_disponibili
        else:
            punti_scelti = st.sidebar.multiselect("Scegli i punti da plottare:", fogli_disponibili)

        # 3. SETUP STATISTICO (Gauss Sigma Clipping)
        st.sidebar.subheader("Pulizia Dati (Statistica)")
        metodo_dati = st.sidebar.radio("Modalità visualizzazione:", ["Dato Grezzo Completo", "Filtro Sigma (Gauss)"])
        
        n_sigma = 3 # Default
        if metodo_dati == "Filtro Sigma (Gauss)":
            n_sigma = st.sidebar.slider("Seleziona il range Sigma (1=68%, 2=95%, 3=99.7%)", 1.0, 3.0, 2.0, 0.5)

        # CICLO DI ELABORAZIONE PER OGNI PUNTO
        for punto in punti_scelti:
            df = pd.read_excel(uploaded_file, sheet_name=punto)
            
            # Assumiamo: Colonna 0 = Data, Colonna 1 = Distanza, Successive = Angoli
            data_col = df.columns[0]
            df[data_col] = pd.to_datetime(df[data_col])
            df = df.sort_values(by=data_col)
            
            st.write(f"---")
            st.header(f"📍 Punto: {punto}")
            
            # 4. SCELTA COSA PLOTTARE (Distanza/Angoli)
            opzioni_plot = st.multiselect(f"Cosa vuoi visualizzare per {punto}?", 
                                         df.columns[1:].tolist(), 
                                         key=f"opt_{punto}")

            if opzioni_plot:
                # Calcolo Report Range Min/Max
                cols = st.columns(len(opzioni_plot))
                for idx, col_name in enumerate(opzioni_plot):
                    val_min = df[col_name].min()
                    val_max = df[col_name].max()
                    cols[idx].metric(f"Range {col_name}", f"Min: {val_min:.3f}", f"Max: {val_max:.3f}")

                # Generazione Grafico
                fig = go.Figure()

                for col_name in opzioni_plot:
                    temp_df = df.copy()
                    
                    # Applicazione Filtro Sigma se richiesto
                    if metodo_dati == "Filtro Sigma (Gauss)":
                        temp_df = applica_filtro_sigma(temp_df, col_name, n_sigma)

                    # Plot Dati Reali
                    fig.add_trace(go.Scatter(
                        x=temp_df[data_col], y=temp_df[col_name],
                        mode='markers+lines',
                        name=f"{col_name} {'(Filtrato)' if metodo_dati != 'Dato Grezzo Completo' else ''}",
                        line=dict(width=1)
                    ))

                    # Trendline Polinomiale (Grado 3)
                    if len(temp_df) > 4:
                        x_num = np.arange(len(temp_df))
                        z = np.polyfit(x_num, temp_df[col_name], 3)
                        p = np.poly1d(z)
                        fig.add_trace(go.Scatter(
                            x=temp_df[data_col], y=p(x_num),
                            mode='lines',
                            name=f"Trend Polinomiale {col_name}",
                            line=dict(dash='dash', color='red')
                        ))

                # Ottimizzazione Ascisse (Date non sovrapposte)
                fig.update_layout(
                    xaxis=dict(
                        tickformat="%d/%m/%Y",
                        nticks=10, # Limita il numero di etichette per evitare sovrapposizioni
                        tickangle=-45
                    ),
                    hovermode="x unified",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
