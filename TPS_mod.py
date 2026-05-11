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
    Carica tutte le sheet una sola volta (ottimizzazione).
    """
    xl = pd.ExcelFile(uploaded_file)
    return {sheet: xl.parse(sheet) for sheet in xl.sheet_names}


def main():

    st.title("🛰️ Piattaforma DIMOS - Analisi Topografica Avanzata")
    st.markdown("---")

    # --- UPLOAD FILE ---
    st.sidebar.header("1. Caricamento Dati")
    uploaded_file = st.sidebar.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])

    if not uploaded_file:
        st.info("Carica un file Excel per iniziare l'analisi.")
        return

    # Caricamento ottimizzato
    dfs = carica_excel(uploaded_file)
    fogli_disponibili = list(dfs.keys())

    # --- SELEZIONE PUNTI ---
    st.sidebar.header("2. Selezione Punti")
    seleziona_tutti = st.sidebar.checkbox("Seleziona tutti i punti")

    if seleziona_tutti:
        punti_scelti = fogli_disponibili
    else:
        punti_scelti = st.sidebar.multiselect("Seleziona punti", fogli_disponibili)

    # --- ANALISI STATISTICA ---
    st.sidebar.header("3. Analisi Statistica")

    metodo = st.sidebar.radio(
        "Trattamento dati:",
        ["Dati Completi", "Filtro Sigma (Gauss)"]
    )

    n_sigma = 2.0
    if metodo == "Filtro Sigma (Gauss)":
        n_sigma = st.sidebar.slider("Sigma", 1.0, 3.0, 2.0, 0.5)

    if not punti_scelti:
        st.warning("Seleziona almeno un punto.")
        return

    # --- LOOP PUNTI ---
    for punto in punti_scelti:

        df = dfs[punto].copy()

        # pulizia colonne
        df.columns = [str(c).strip() for c in df.columns]

        if len(df.columns) < 2:
            st.warning(f"{punto}: dati insufficienti")
            continue

        colonna_data = df.columns[0]

        # conversione date
        df[colonna_data] = pd.to_datetime(df[colonna_data], errors='coerce')
        df = df.dropna(subset=[colonna_data])

        st.write(f"## 📍 Punto: {punto}")

        colonne_numeriche = df.columns[1:].tolist()

        if not colonne_numeriche:
            st.warning("Nessuna colonna numerica trovata")
            continue

        scelte = st.multiselect(
            f"Dati da plottare - {punto}",
            colonne_numeriche,
            default=[colonne_numeriche[0]],
            key=punto
        )

        if not scelte:
            continue

        # --- METRICHE RANGE ---
        cols = st.columns(len(scelte))

        for i, col in enumerate(scelte):
            serie = pd.to_numeric(df[col], errors='coerce').dropna()

            if serie.empty:
                continue

            cols[i].metric(
                f"{col}",
                f"Max: {serie.max():.3f}",
                f"Min: {serie.min():.3f} | Δ {(serie.max()-serie.min()):.3f}"
            )

        # --- GRAFICO ---
        fig = go.Figure()

        for col in scelte:

            serie = pd.to_numeric(df[col], errors='coerce')
            df_plot = df[[colonna_data]].copy()
            df_plot[col] = serie
            df_plot = df_plot.dropna()

            if df_plot.empty:
                continue

            # =========================
            # FILTRO SIGMA
            # =========================
            if metodo == "Filtro Sigma (Gauss)":
                df_plot[col] = applica_filtro_sigma(df_plot[col], n_sigma)

            df_plot = df_plot.dropna()

            if df_plot.empty:
                continue

            # --- DATI ---
            fig.add_trace(go.Scatter(
                x=df_plot[colonna_data],
                y=df_plot[col],
                mode='markers+lines',
                name=f"{col} (dati)",
                marker=dict(size=4),
                line=dict(width=1)
            ))

            # --- TRENDLINE (CORRETTA SU DATE REALI) ---
            if len(df_plot) > 4:

                x = df_plot[colonna_data].map(pd.Timestamp.toordinal).values
                y = df_plot[col].values

                coeff = np.polyfit(x, y, 3)
                poly = np.poly1d(coeff)

                fig.add_trace(go.Scatter(
                    x=df_plot[colonna_data],
                    y=poly(x),
                    mode='lines',
                    name=f"{col} (trend)",
                    line=dict(width=2, dash='dot', color='red')
                ))

        # --- LAYOUT ---
        fig.update_layout(
            template="plotly_white",
            height=600,
            hovermode="x unified",
            legend=dict(orientation="h"),
            xaxis=dict(
                title="Data",
                tickformat="%d/%m/%Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                title="Valore",
                showgrid=True
            )
        )

        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
