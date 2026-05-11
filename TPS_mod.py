import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Analisi Topografica Avanzata", layout="wide")

def applica_filtro_sigma(df, colonna, n_sigma):
    """
    Rimuove i dati che superano il numero di Sigma impostato (Curva di Gauss).
    """
    # Assicuriamoci che il dato sia numerico e senza NaN per il calcolo statistico
    valori_puliti = pd.to_numeric(df[colonna], errors='coerce').dropna()
    if valori_puliti.empty:
        return df
    
    media = valori_puliti.mean()
    std = valori_puliti.std()
    
    limite_inf = media - n_sigma * std
    limite_sup = media + n_sigma * std
    
    # Filtriamo il dataframe originale mantenendo le righe nei limiti
    return df[(pd.to_numeric(df[colonna], errors='coerce') >= limite_inf) & 
              (pd.to_numeric(df[colonna], errors='coerce') <= limite_sup)]

def main():
    st.title("🛰️ Piattaforma DIMOS - Elaborazione Dati")
    st.markdown("---")

    # --- 1. UPLOAD DEL FILE ---
    st.sidebar.header("1. Caricamento Dati")
    uploaded_file = st.sidebar.file_uploader("Carica il file Excel (.xlsx)", type=["xlsx"])

    if uploaded_file:
        # Carichiamo l'oggetto Excel per leggere i nomi dei fogli
        xl = pd.ExcelFile(uploaded_file)
        fogli_disponibili = xl.sheet_names
        
        # --- 2. SELEZIONE PUNTI (CHECKBOX) ---
        st.sidebar.header("2. Selezione Punti")
        seleziona_tutti = st.sidebar.checkbox("Seleziona tutti i punti disponibili")
        
        if seleziona_tutti:
            punti_scelti = fogli_disponibili
        else:
            punti_scelti = st.sidebar.multiselect("Quali punti vuoi analizzare?", fogli_disponibili)

        # --- 3. SETUP STATISTICO (GAUSS) ---
        st.sidebar.header("3. Analisi Statistica")
        metodo_dati = st.sidebar.radio("Trattamento dati:", 
                                      ["Dato Prezzo Completo", "Filtro Sigma (Gauss)"])
        
        n_sigma = 2.0
        if metodo_dati == "Filtro Sigma (Gauss)":
            n_sigma = st.sidebar.slider("Soglia Sigma (Deviazione Standard):", 1.0, 3.0, 2.0, 0.5)
            st.sidebar.info(f"Verranno eliminati i dati oltre {n_sigma}σ dalla media.")

        # --- ELABORAZIONE GRAFICI ---
        if not punti_scelti:
            st.warning("Seleziona almeno un punto dalla barra laterale per visualizzare i grafici.")
        
        for punto in punti_scelti:
            # Caricamento del singolo foglio
            df = pd.read_excel(uploaded_file, sheet_name=punto)
            
            # Gestione Intestazioni: Assumiamo 1° colonna = Data
            # Pulizia per evitare l'errore 'invalid literal for int()'
            df.columns = [str(c).strip() for c in df.columns]
            colonna_data = df.columns[0]
            df[colonna_data] = pd.to_datetime(df[colonna_data], errors='coerce')
            df = df.dropna(subset=[colonna_data]) # Rimuove righe dove la data è testo o vuota
            
            st.write(f"## 📍 Analisi Punto: {punto}")
            
            # --- 4. SELEZIONE COSA PLOTTARE ---
            # Filtriamo le colonne numeriche (escludendo la data)
            colonne_numeriche = df.columns[1:].tolist()
            scelte_utente = st.multiselect(f"Cosa vuoi plottare per {punto}?", 
                                         colonne_numeriche, 
                                         default=[colonne_numeriche[0]] if colonne_numeriche else [],
                                         key=f"multi_{punto}")

            if scelte_utente:
                # --- REPORT RANGE MIN/MAX ---
                cols_metrics = st.columns(len(scelte_utente))
                for idx, col_name in enumerate(scelte_utente):
                    # Convertiamo in numerico per sicurezza
                    ser_num = pd.to_numeric(df[col_name], errors='coerce').dropna()
                    if not ser_num.empty:
                        cols_metrics[idx].metric(f"Range {col_name}", 
                                               f"Max: {ser_num.max():.3f}", 
                                               f"Min: {ser_num.min():.3f}")

                # --- GENERAZIONE GRAFICO INTERATTIVO ---
                fig = go.Figure()

                for col_name in scelte_utente:
                    # Copia locale per non sporcare il DF principale
                    df_plot = df.copy()
                    
                    # Applichiamo Gauss se richiesto
                    if metodo_dati == "Filtro Sigma (Gauss)":
                        df_plot = applica_filtro_sigma(df_plot, col_name, n_sigma)
                    
                    # Pulizia finale valori per il plot
                    df_plot[col_name] = pd.to_numeric(df_plot[col_name], errors='coerce')
                    df_plot = df_plot.dropna(subset=[col_name])
                    
                    if df_plot.empty:
                        continue

                    # 1. Plot Dati (Scatter + Linee sottili)
                    fig.add_trace(go.Scatter(
                        x=df_plot[colonna_data], 
                        y=df_plot[col_name],
                        mode='markers+lines',
                        name=f"{col_name} (Dati)",
                        marker=dict(size=4),
                        line=dict(width=1, color='rgba(0, 112, 192, 0.5)')
                    ))

                    # 2. Trendline Polinomiale (Grado 3)
                    if len(df_plot) > 4:
                        # Usiamo un indice numerico per il fit (per gestire le date)
                        x_idx = np.arange(len(df_plot))
                        y_val = df_plot[col_name].values
                        
                        coeffs = np.polyfit(x_idx, y_val, 3)
                        poly_func = np.poly1d(coeffs)
                        
                        fig.add_trace(go.Scatter(
                            x=df_plot[colonna_data], 
                            y=poly_func(x_idx),
                            mode='lines',
                            name=f"Tendenza {col_name} (Polinomiale)",
                            line=dict(color='red', width=2, dash='dot')
                        ))

                # --- 5. OTTIMIZZAZIONE ASSI (DATE) ---
                fig.update_layout(
                    template="plotly_white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=40, r=40, t=80, b=40),
                    hovermode="x unified",
                    xaxis=dict(
                        title="Data Rilievo",
                        tickformat="%d/%m/%Y",
                        tickangle=-45,
                        nticks=15, # Impedisce la sovrapposizione delle date
                        showgrid=True,
                        gridcolor='lightgrey'
                    ),
                    yaxis=dict(
                        title="Valore Misurato",
                        showgrid=True,
                        gridcolor='lightgrey'
                    ),
                    height=600
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Seleziona almeno un sensore (Distanza o Angolo) per il punto {punto}.")

    else:
        # Messaggio di benvenuto se nessun file è caricato
        st.info("👋 Benvenuto! Carica un file Excel nella barra laterale per iniziare l'analisi.")

if __name__ == "__main__":
    main()
