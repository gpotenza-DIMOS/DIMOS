import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="DIMOS - Analisi Topografica Avanzata", layout="wide")

def applica_filtro_sigma(serie, n_sigma):
    """
    Filtro Gauss (Sigma) su serie numerica già pulita.
    """
    media = serie.mean()
    std = serie.std()
    if pd.isna(std) or std == 0:
        return serie
    limite_inf = media - n_sigma * std
    limite_sup = media + n_sigma * std
    return serie.where((serie >= limite_inf) & (serie <= limite_sup))

@st.cache_data
def carica_excel(uploaded_file):
    """
    Carica tutte le sheet una sola volta.
    """
    xl = pd.ExcelFile(uploaded_file)
    return {sheet: xl.parse(sheet) for sheet in xl.sheet_names}

def main():
    st.title("🛰️ Piattaforma DIMOS - Analisi Topografica Avanzata")
    st.markdown("---")

    # --- 1. UPLOAD FILE ---
    st.sidebar.header("1. Caricamento Dati")
    uploaded_file = st.sidebar.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])

    if not uploaded_file:
        st.info("Carica un file Excel per iniziare l'analisi.")
        return

    dfs = carica_excel(uploaded_file)
    fogli_disponibili = list(dfs.keys())

    # --- 2. SELEZIONE PUNTI ---
    st.sidebar.header("2. Selezione Punti")
    seleziona_tutti = st.sidebar.checkbox("Seleziona tutti i punti")
    punti_scelti = fogli_disponibili if seleziona_tutti else st.sidebar.multiselect("Seleziona punti", fogli_disponibili)

    # --- 3. ANALISI STATISTICA ---
    st.sidebar.header("3. Analisi Statistica")
    metodo = st.sidebar.radio("Trattamento dati:", ["Dati Completi", "Filtro Sigma (Gauss)"])
    n_sigma = st.sidebar.slider("Sigma (Soglia Gauss)", 1.0, 3.0, 2.0, 0.5) if metodo == "Filtro Sigma (Gauss)" else 2.0

    if not punti_scelti:
        st.warning("Seleziona almeno un punto dalla barra laterale.")
        return

    # --- LOOP PUNTI ---
    for punto in punti_scelti:
        df = dfs[punto].copy()
        df.columns = [str(c).strip() for c in df.columns]

        if len(df.columns) < 2:
            continue

        colonna_data = df.columns[0]
        df[colonna_data] = pd.to_datetime(df[colonna_data], errors='coerce')
        df = df.dropna(subset=[colonna_data]).sort_values(by=colonna_data)

        st.write(f"## 📍 Punto: {punto}")
        colonne_numeriche = [c for c in df.columns[1:] if not c.lower().startswith('unnamed')]

        scelte = st.multiselect(f"Dati da plottare - {punto}", colonne_numeriche, 
                                default=[colonne_numeriche[0]] if colonne_numeriche else [], key=f"sel_{punto}")

        if not scelte:
            continue

        # --- METRICHE RANGE ---
        cols_met = st.columns(len(scelte))
        for i, col in enumerate(scelte):
            serie_clean = pd.to_numeric(df[col], errors='coerce').dropna()
            if not serie_clean.empty:
                val_min, val_max = serie_clean.min(), serie_clean.max()
                cols_met[i].metric(col, f"Max: {val_max:.3f}", f"Min: {val_min:.3f}")

        # --- GRAFICO ---
        fig = go.Figure()
        for col in scelte:
            df_plot = df[[colonna_data, col]].copy()
            df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
            df_plot = df_plot.dropna()

            if metodo == "Filtro Sigma (Gauss)":
                df_plot[col] = applica_filtro_sigma(df_plot[col], n_sigma)
                df_plot = df_plot.dropna()

            if df_plot.empty:
                continue

            # Plot Dati Reali
            fig.add_trace(go.Scatter(x=df_plot[colonna_data], y=df_plot[col],
                                     mode='markers+lines', name=f"{col} (dati)",
                                     marker=dict(size=5), line=dict(width=1.5)))

            # Trendline Polinomiale (Normalizzata per evitare errori numerici)
            if len(df_plot) > 4:
                # Trasformiamo le date in un range 0 - N per la stabilità del calcolo
                x_numeric = np.arange(len(df_plot)) 
                y_values = df_plot[col].values
                
                coeff = np.polyfit(x_numeric, y_values, 3)
                poly = np.poly1d(coeff)

                fig.add_trace(go.Scatter(x=df_plot[colonna_data], y=poly(x_numeric),
                                         mode='lines', name=f"{col} (trend)",
                                         line=dict(width=2.5, dash='dash', color='red')))

        # --- LAYOUT OTTIMIZZATO ---
        fig.update_layout(
            template="plotly_white", height=550,
            hovermode="x unified",
            xaxis=dict(
                title="Data Rilievo",
                tickformat="%d/%m/%Y",
                tickangle=-45,
                nticks=20, # Forza Plotly a non sovrapporre le date
                showgrid=True
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
