import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def applica_filtri_completi(serie, n_sigma, rimuovi_zeri):
    originale = serie.copy()
    diag = {"zeri": 0, "gauss": 0}
    if rimuovi_zeri:
        diag["zeri"] = (originale == 0).sum()
        originale = originale.replace(0, np.nan)
    validi = originale.dropna()
    if not validi.empty and n_sigma > 0:
        mean, std = validi.mean(), validi.std()
        if std > 0:
            lower, upper = mean - n_sigma * std, mean + n_sigma * std
            outliers = (originale < lower) | (originale > upper)
            diag["gauss"] = outliers.sum()
            originale[outliers] = np.nan
    return originale, diag

def main():
    st.title("📈 Plotter Professionale Gerarchico")

    uploaded_file = st.file_uploader("Carica Excel con foglio NAME", type=["xlsx"])

    if uploaded_file:
        # Carichiamo il foglio dati (il primo) e il foglio NAME
        xls = pd.ExcelFile(uploaded_file)
        df_data = pd.read_excel(xls, sheet_name=0)
        
        if "NAME" in xls.sheet_names:
            df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
            
            # --- COSTRUZIONE GERARCHIA UNICA ---
            # Struttura: { 'Datalogger_A': { 'Sensore_1': [colonna_web_X, colonna_web_Y] } }
            gerarchia = {}
            
            # Saltiamo la prima colonna (solitamente 'Data e Ora')
            for i in range(1, df_name.shape[1]):
                dl_nome = str(df_name.iloc[0, i]).strip() # Riga 1
                sens_nome = str(df_name.iloc[1, i]).strip() # Riga 2
                col_web = str(df_name.iloc[2, i]).strip() # Riga 3 (nome colonna nel df_data)
                
                if dl_nome not in gerarchia:
                    gerarchia[dl_nome] = {}
                if sens_nome not in gerarchia[dl_nome]:
                    gerarchia[dl_nome][sens_nome] = []
                
                gerarchia[dl_nome][sens_nome].append(col_web)

            # --- UI SIDEBAR ---
            st.sidebar.header("🗂️ Selezione Gerarchica")
            
            # 1. Scelta Datalogger (univoci)
            scelta_dl = st.sidebar.multiselect("Seleziona Datalogger", list(gerarchia.keys()))
            
            colonne_da_graficare = []
            
            for dl in scelta_dl:
                st.sidebar.markdown(f"---")
                st.sidebar.subheader(f"📟 {dl}")
                
                # 2. Scelta Sensori (univoci per quel datalogger)
                sensori_disp = list(gerarchia[dl].keys())
                scelta_sens = st.sidebar.multiselect(f"Sensori collegati a {dl}", sensori_disp, key=f"s_{dl}")
                
                for s in scelta_sens:
                    # 3. Prendi tutte le grandezze fisiche (colonne) di quel sensore
                    colonne_da_graficare.extend(gerarchia[dl][s])

            # --- FILTRI ---
            st.sidebar.divider()
            rimuovi_zeri = st.sidebar.checkbox("Rimuovi Zeri", value=True)
            sigma = st.sidebar.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
            
            # --- ASSE X ---
            col_tempo = df_data.columns[0]
            df_data[col_tempo] = pd.to_datetime(df_data[col_tempo])
            modo_x = st.sidebar.radio("Asse X", ["Data Ora", "Testo (Equidistante)"])

            # --- GRAFICO ---
            if colonne_da_graficare:
                fig = go.Figure()
                for col in colonne_da_graficare:
                    if col in df_data.columns:
                        y_pulita, _ = applica_filtri_completi(df_data[col], sigma, rimuovi_zeri)
                        
                        x_axis = df_data[col_tempo]
                        if modo_x == "Testo (Equidistante)":
                            x_axis = df_data[col_tempo].dt.strftime('%d/%m/%y %H:%M')

                        fig.add_trace(go.Scatter(
                            x=x_axis, 
                            y=y_pulita, 
                            name=col,
                            mode='lines+markers'
                        ))
                
                fig.update_layout(template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Seleziona i componenti dalla sidebar per visualizzare i grafici.")
        else:
            st.error("Il foglio 'NAME' non è stato trovato nel file!")

if __name__ == "__main__":
    main()
