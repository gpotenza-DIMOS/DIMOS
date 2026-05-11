import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Analisi Topografica", layout="wide")
warnings.simplefilter('ignore', np.RankWarning)

def applica_filtro_sigma(serie, n_sigma):
    media = serie.mean()
    std = serie.std()
    if pd.isna(std) or std == 0:
        return serie
    return serie.where((serie >= media - n_sigma * std) & (serie <= media + n_sigma * std))

@st.cache_data
def carica_excel(uploaded_file):
    xl = pd.ExcelFile(uploaded_file)
    # Carichiamo i fogli pulendo subito i nomi delle colonne da spazi bianchi
    data = {}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        df.columns = [str(c).strip() for c in df.columns]
        data[sheet] = df
    return data

def main():
    st.title("🛰️ Piattaforma DIMOS - Analisi Topografica")
    st.markdown("---")

    st.sidebar.header("1. Caricamento Dati")
    uploaded_file = st.sidebar.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])

    if not uploaded_file:
        st.info("In attesa del file Excel...")
        return

    dfs = carica_excel(uploaded_file)
    fogli_disponibili = list(dfs.keys())

    st.sidebar.header("2. Selezione Punti")
    seleziona_tutti = st.sidebar.checkbox("Seleziona tutti i punti")
    punti_scelti = fogli_disponibili if seleziona_tutti else st.sidebar.multiselect("Seleziona punti", fogli_disponibili)

    st.sidebar.header("3. Analisi Statistica")
    metodo = st.sidebar.radio("Trattamento dati:", ["Dati Completi", "Filtro Sigma (Gauss)"])
    n_sigma = st.sidebar.slider("Sigma", 1.0, 3.0, 2.0, 0.5) if metodo == "Filtro Sigma (Gauss)" else 2.0

    if not punti_scelti:
        st.warning("Seleziona almeno un punto per visualizzare i risultati.")
        return

    for punto in punti_scelti:
        df = dfs[punto].copy()
        
        if df.empty or len(df.columns) < 2:
            st.error(f"Il foglio '{punto}' appare vuoto o malformato.")
            continue

        # IDENTIFICAZIONE DINAMICA DELLA COLONNA TEMPORALE (La prima)
        colonna_data = df.columns[0]
        df[colonna_data] = pd.to_datetime(df[colonna_data], errors='coerce')
        df = df.dropna(subset=[colonna_data]).sort_values(by=colonna_data)

        st.write(f"## 📍 Analisi Punto: {punto}")
        
        # Filtriamo le colonne: solo quelle che contengono dati numerici reali
        colonne_numeriche = []
        for c in df.columns[1:]:
            if not "Unnamed" in c:
                # Verifichiamo se la colonna ha almeno un numero
                if pd.to_numeric(df[c], errors='coerce').notnull().any():
                    colonne_numeriche.append(c)

        scelte = st.multiselect(f"Sensori disponibili per {punto}", colonne_numeriche, 
                                default=[colonne_numeriche[0]] if colonne_numeriche else [], key=f"ms_{punto}")

        if not scelte:
            st.info("Seleziona uno o più sensori dal menu sopra.")
            continue

        # Metriche
        cols_m = st.columns(len(scelte))
        for i, col in enumerate(scelte):
            valori_temporanei = pd.to_numeric(df[col], errors='coerce').dropna()
            if not valori_temporanei.empty:
                diff = valori_temporanei.max() - valori_temporanei.min()
                cols_m[i].metric(col, f"{valori_temporanei.iloc[-1]:.3f}", f"Δ {diff:.3f}")

        # Grafico Plotly
        fig = go.Figure()
        for col in scelte:
            d_p = df[[colonna_data, col]].copy()
            d_p[col] = pd.to_numeric(d_p[col], errors='coerce')
            d_p = d_p.dropna()

            if metodo == "Filtro Sigma (Gauss)":
                d_p[col] = applica_filtro_sigma(d_p[col], n_sigma)
                d_p = d_p.dropna()

            if len(d_p) < 2:
                continue

            # Linea Dati
            fig.add_trace(go.Scatter(x=d_p[colonna_data], y=d_p[col], name=f"{col}", mode='lines+markers'))

            # Trendline Polinomiale (Solo se ci sono abbastanza punti)
            if len(d_p) >= 5:
                try:
                    x_idx = np.arange(len(d_p))
                    coeff = np.polyfit(x_idx, d_p[col].values, 3)
                    poly = np.poly1d(coeff)
                    fig.add_trace(go.Scatter(x=d_p[colonna_data], y=poly(x_idx),
                                             name=f"Trend {col}", line=dict(dash='dot', width=2)))
                except:
                    pass

        fig.update_layout(
            template="plotly_white", height=500,
            hovermode="x unified",
            xaxis=dict(title="Data", tickformat="%d/%m/%y", tickangle=-45, nticks=15),
            yaxis=dict(title="Valore Misurato")
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
