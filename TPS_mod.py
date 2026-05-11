import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Analisi Topografica Avanzata", layout="wide")

# Disabilita i warning fastidiosi di Rank nella console
warnings.simplefilter('ignore', np.RankWarning)

def applica_filtro_sigma(serie, n_sigma):
    media = serie.mean()
    std = serie.std()
    if pd.isna(std) or std == 0:
        return serie
    limite_inf = media - n_sigma * std
    limite_sup = media + n_sigma * std
    return serie.where((serie >= limite_inf) & (serie <= limite_sup))

@st.cache_data
def carica_excel(uploaded_file):
    xl = pd.ExcelFile(uploaded_file)
    return {sheet: xl.parse(sheet) for sheet in xl.sheet_names}

def main():
    st.title("🛰️ Piattaforma DIMOS - Analisi Topografica")
    st.markdown("---")

    st.sidebar.header("1. Caricamento Dati")
    uploaded_file = st.sidebar.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])

    if not uploaded_file:
        st.info("Carica un file Excel per iniziare.")
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
        st.warning("Seleziona almeno un punto.")
        return

    for punto in punti_scelti:
        df = dfs[punto].copy()
        df.columns = [str(c).strip() for c in df.columns]

        if len(df.columns) < 2: continue

        colonna_data = df.columns[0]
        df[colonna_data] = pd.to_datetime(df[colonna_data], errors='coerce')
        df = df.dropna(subset=[colonna_data]).sort_values(by=colonna_data)

        st.write(f"## 📍 Punto: {punto}")
        
        # Escludiamo colonne non numeriche o "Unnamed"
        colonne_numeriche = [c for c in df.columns[1:] if "Unnamed" not in c]
        scelte = st.multiselect(f"Sensori per {punto}", colonne_numeriche, 
                                default=[colonne_numeriche[0]] if colonne_numeriche else [], key=f"s_{punto}")

        if not scelte: continue

        # Visualizzazione Metriche
        cols_m = st.columns(len(scelte))
        for i, col in enumerate(scelte):
            s_val = pd.to_numeric(df[col], errors='coerce').dropna()
            if not s_val.empty:
                cols_m[i].metric(col, f"{s_val.iloc[-1]:.3f}", f"Δ {s_val.max()-s_val.min():.3f}")

        # Grafico
        fig = go.Figure()
        for col in scelte:
            # Creiamo un subset pulito per ogni colonna
            d_p = df[[colonna_data, col]].copy()
            d_p[col] = pd.to_numeric(d_p[col], errors='coerce')
            d_p = d_p.dropna()

            if metodo == "Filtro Sigma (Gauss)":
                d_p[col] = applica_filtro_sigma(d_p[col], n_sigma)
                d_p = d_p.dropna()

            if len(d_p) < 2: continue

            # Scatter Dati
            fig.add_trace(go.Scatter(x=d_p[colonna_data], y=d_p[col], name=f"{col}", mode='lines+markers'))

            # Trendline Polinomiale con CONTROLLO PUNTI
            # Servono almeno 5 punti per un grado 3 sensato
            if len(d_p) >= 5:
                try:
                    x_num = np.arange(len(d_p))
                    y_num = d_p[col].values
                    coeff = np.polyfit(x_num, y_num, 3)
                    poly = np.poly1d(coeff)
                    
                    fig.add_trace(go.Scatter(
                        x=d_p[colonna_data], y=poly(x_num),
                        name=f"Trend {col}", line=dict(dash='dot', color='red', width=2)
                    ))
                except Exception:
                    pass # Se il calcolo fallisce ancora, salta la trendline senza bloccare l'app

        fig.update_layout(template="plotly_white", height=500, hovermode="x unified",
                          xaxis=dict(tickformat="%d/%m/%y", tickangle=-45, nticks=15))
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
