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
    st.set_page_config(page_title="DIMOS Plotter", layout="wide")
    st.title("📈 Analisi Monitoraggio Strutturale")

    uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])

    if uploaded_file:
        try:
            xls = pd.ExcelFile(uploaded_file)
            # Carichiamo il foglio dati (assumiamo sia il primo)
            df_data = pd.read_excel(xls, sheet_name=0)
            
            if "NAME" in xls.sheet_names:
                # Carichiamo NAME senza header per gestire noi le righe 1, 2, 3
                df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
                
                # --- PULIZIA E COSTRUZIONE DIZIONARIO UNICO ---
                # Struttura: { 'Datalogger': { 'Sensore': [Lista Grandezze Web] } }
                gerarchia = {}
                
                # Iteriamo sulle colonne del foglio NAME
                # Partiamo dalla colonna che non è "datalogger" (solitamente la colonna A è l'indice)
                for col_idx in range(df_name.shape[1]):
                    # Leggiamo i valori delle 3 righe
                    r1_dl = str(df_name.iloc[0, col_idx]).strip()
                    r2_sens = str(df_name.iloc[1, col_idx]).strip()
                    r3_web = str(df_name.iloc[2, col_idx]).strip()
                    
                    # Saltiamo le intestazioni o celle vuote
                    if r1_dl.lower() in ["datalogger", "nan"] or r3_web.lower() == "nan":
                        continue
                    
                    if r1_dl not in gerarchia:
                        gerarchia[r1_dl] = {}
                    if r2_sens not in gerarchia[r1_dl]:
                        gerarchia[r1_dl][r2_sens] = []
                    
                    # Aggiungiamo il "nome web" (riga 3) alla lista del sensore
                    if r3_web in df_data.columns:
                        gerarchia[r1_dl][r2_sens].append(r3_web)

                # --- INTERFACCIA DI SELEZIONE ---
                st.sidebar.header("🕹️ Pannello di Controllo")
                
                # 1. Selezione Datalogger (Univoci)
                lista_dl = sorted(list(gerarchia.keys()))
                sel_dl = st.sidebar.multiselect("Seleziona Centraline", lista_dl)
                
                colonne_finali = []
                
                if sel_dl:
                    for dl in sel_dl:
                        st.sidebar.markdown(f"**--- {dl} ---**")
                        # 2. Selezione Sensori (Univoci per quel DL)
                        lista_sens = sorted(list(gerarchia[dl].keys()))
                        sel_sens = st.sidebar.multiselect(f"Sensori in {dl}", lista_sens, key=f"sel_{dl}")
                        
                        for s in sel_sens:
                            # 3. Raccogliamo tutte le grandezze fisiche del sensore scelto
                            colonne_finali.extend(gerarchia[dl][s])

                # --- FILTRI E OPZIONI ---
                st.sidebar.divider()
                rimuovi_zeri = st.sidebar.checkbox("Elimina letture a Zero", value=True)
                sigma = st.sidebar.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
                
                # Gestione asse X
                col_tempo = df_data.columns[0] # La prima colonna del primo foglio
                df_data[col_tempo] = pd.to_datetime(df_data[col_tempo], errors='coerce')
                modo_x = st.sidebar.radio("Modalità Asse X", ["Data Ora", "Equidistante (Testo)"])

                # --- GENERAZIONE GRAFICO ---
                if colonne_finali:
                    fig = go.Figure()
                    
                    for col in colonne_finali:
                        # Applicazione Gauss e Zeri
                        y_vals, info = applica_filtri_completi(df_data[col], sigma, rimuovi_zeri)
                        
                        x_vals = df_data[col_tempo]
                        if modo_x == "Equidistante (Testo)":
                            x_vals = df_data[col_tempo].dt.strftime('%d/%m/%y %H:%M')

                        fig.add_trace(go.Scatter(
                            x=x_vals,
                            y=y_vals,
                            name=col,
                            mode='lines+markers',
                            connectgaps=False # Non unisce i punti eliminati dai filtri
                        ))

                    fig.update_layout(
                        template="plotly_white",
                        hovermode="x unified",
                        xaxis_title="Asse Temporale",
                        yaxis_title="Valore Misurato",
                        legend=dict(orientation="h", y=-0.2)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Anteprima dati filtrati
                    with st.expander("🔍 Tabella Dati Selezionati (Primi 100)"):
                        st.dataframe(df_data[[col_tempo] + colonne_finali].head(100))
                else:
                    st.warning("Seleziona almeno un datalogger e un sensore per visualizzare i dati.")

        except Exception as e:
            st.error(f"Si è verificato un errore nel parsing: {e}")
            st.info("Assicurati che il foglio 'NAME' abbia: Riga 1 (DL), Riga 2 (Sensore), Riga 3 (Nome Web).")

if __name__ == "__main__":
    main()
