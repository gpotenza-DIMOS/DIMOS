import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

# --- LOGICA DI FILTRAGGIO ---
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

# --- PARSING GERARCHIA ---
def costruisci_gerarchia(df_data, xls_obj):
    gerarchia = {}
    
    # Caso A: Esiste il foglio NAME
    if "NAME" in xls_obj.sheet_names:
        df_name = pd.read_excel(xls_obj, sheet_name="NAME", header=None)
        for col_idx in range(df_name.shape[1]):
            try:
                dl = str(df_name.iloc[0, col_idx]).strip()
                sensore = str(df_name.iloc[1, col_idx]).strip()
                grandezza = str(df_name.iloc[2, col_idx]).strip()
                
                if dl.lower() in ["nan", "datalogger"] or grandezza not in df_data.columns:
                    continue
                
                if dl not in gerarchia: gerarchia[dl] = {}
                if sensore not in gerarchia[dl]: gerarchia[dl][sensore] = []
                gerarchia[dl][sensore].append(grandezza)
            except: continue
            
    # Caso B: Parsing dal nome colonna (Fallback)
    else:
        for col in df_data.columns[1:]: # Salta la colonna tempo
            parts = col.split(" ")
            if len(parts) >= 2:
                # Es: CO_9277 CL_01_X [°] -> DL: CO_9277, Sensore: CL_01
                dl = parts[0]
                # Cerchiamo di capire se c'è un sotto-id sensore (es. CL_01)
                sub_parts = parts[1].split("_")
                sensore = f"{parts[0]}_{sub_parts[0]}_{sub_parts[1]}" if len(sub_parts) >= 2 else parts[0]
                
                if dl not in gerarchia: gerarchia[dl] = {}
                if sensore not in gerarchia[dl]: gerarchia[dl][sensore] = []
                gerarchia[dl][sensore].append(col)
            else:
                dl = "Generali"
                if dl not in gerarchia: gerarchia[dl] = {"Sensori": []}
                gerarchia[dl]["Sensori"].append(col)
                
    return gerarchia

def main():
    st.set_page_config(page_title="DIMOS Structural Plotter", layout="wide")
    st.title("🏗️ DIMOS - Monitoraggio Strutturale")

    uploaded_file = st.file_uploader("1. Carica il file Excel (.xlsx)", type=["xlsx"])

    if uploaded_file:
        xls = pd.ExcelFile(uploaded_file)
        # Carica il primo foglio come dati
        df_data = pd.read_excel(xls, sheet_name=0)
        col_tempo = df_data.columns[0]
        df_data[col_tempo] = pd.to_datetime(df_data[col_tempo], errors='coerce')
        
        # Costruzione gerarchia DL -> Sensore -> Grandezze
        gerarchia = costruisci_gerarchia(df_data, xls)

        # --- SEZIONE SELEZIONE (Pagina Principale) ---
        st.subheader("2. Selezione Dati")
        c1, c2 = st.columns(2)
        
        with c1:
            lista_dl = sorted(list(gerarchia.keys()))
            sel_dls = st.multiselect("Seleziona Centraline (Datalogger)", lista_dl)
            
        colonne_da_plottare = []
        if sel_dls:
            with c2:
                # Uniamo i sensori di tutte le centraline selezionate
                sensori_disponibili = {}
                for dl in sel_dls:
                    for s, cols in gerarchia[dl].items():
                        sensori_disponibili[f"{dl} > {s}"] = cols
                
                sel_sens = st.multiselect("Seleziona Sensori", list(sensori_disponibili.keys()))
                for s in sel_sens:
                    colonne_da_plottare.extend(sensori_disponibili[s])

        # --- FILTRI ---
        st.divider()
        with st.expander("🛠️ Impostazioni Analisi e Filtri", expanded=True):
            f1, f2, f3 = st.columns(3)
            with f1:
                rimuovi_zeri = st.checkbox("Elimina letture a '0'", value=True)
                sigma = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 3.0)
            with f2:
                modo_x = st.radio("Asse X", ["Temporale", "Equidistante (Indici)"])
            with f3:
                st.write("Esportazioni")
                if st.button("Esporta Ascisse (.txt)"):
                    txt_data = df_data[col_tempo].dt.strftime('%d/%m/%Y %H:%M:%S').to_string(index=False)
                    st.download_button("Scarica TXT", txt_data, "ascisse_monitoraggio.txt")

        # --- GRAFICO ---
        if colonne_da_plottare:
            fig = go.Figure()
            stats = []

            for col in colonne_da_plottare:
                y_filtrata, info = applica_filtri_completi(df_data[col], sigma, rimuovi_zeri)
                stats.append({"Colonna": col, "Zeri rimossi": info["zeri"], "Outliers (Gauss)": info["gauss"]})
                
                x_vals = df_data[col_tempo] if modo_x == "Temporale" else df_data.index
                
                fig.add_trace(go.Scatter(
                    x=x_vals, y=y_filtrata, name=col,
                    mode='lines+markers', marker=dict(size=4),
                    connectgaps=False
                ))

            fig.update_layout(
                height=650,
                template="plotly_white",
                hovermode="x unified",
                legend=dict(orientation="h", y=-0.15)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabella Diagnostica
            st.write("### 📊 Diagnostica Filtri")
            st.table(pd.DataFrame(stats))
        else:
            st.info("Inizia selezionando una centralina per visualizzare i sensori collegati.")

if __name__ == "__main__":
    main()
