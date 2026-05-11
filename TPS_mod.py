import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import logging
import warnings

# =========================
# CONFIGURAZIONE APP
# =========================
st.set_page_config(page_title="DIMOS - Analisi Topografica", layout="wide")

warnings.simplefilter("ignore", np.RankWarning)


# =========================
# LOGGER
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("DIMOS")


# =========================
# FUNZIONE SIGMA FILTER
# =========================
def applica_filtro_sigma(serie, n_sigma):
    try:
        media = serie.mean()
        std = serie.std()

        if pd.isna(std) or std == 0:
            return serie

        return serie.where(
            (serie >= media - n_sigma * std) &
            (serie <= media + n_sigma * std)
        )

    except Exception as e:
        logger.error(f"Errore filtro sigma: {e}")
        return serie


# =========================
# CARICAMENTO EXCEL OTTIMIZZATO
# =========================
@st.cache_data
def carica_excel(uploaded_file):
    try:
        xl = pd.ExcelFile(uploaded_file)

        data = {}
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            df.columns = [str(c).strip() for c in df.columns]
            data[sheet] = df

        return data

    except Exception as e:
        logger.error(f"Errore caricamento Excel: {e}")
        return {}


# =========================
# MAIN APP
# =========================
def main():

    st.title("🛰️ DIMOS - Analisi Topografica Avanzata")
    st.markdown("---")

    # -------------------------
    # UPLOAD FILE
    # -------------------------
    st.sidebar.header("1. Caricamento Dati")
    uploaded_file = st.sidebar.file_uploader("Carica Excel (.xlsx)", type=["xlsx"])

    if not uploaded_file:
        st.info("Carica un file Excel per iniziare.")
        return

    dfs = carica_excel(uploaded_file)
    fogli = list(dfs.keys())

    if not fogli:
        st.error("File Excel non valido o vuoto.")
        return

    # -------------------------
    # SELEZIONE FOGLI
    # -------------------------
    st.sidebar.header("2. Selezione Punti")

    seleziona_tutti = st.sidebar.checkbox("Seleziona tutti i punti")

    punti = fogli if seleziona_tutti else st.sidebar.multiselect(
        "Seleziona punti",
        fogli
    )

    # -------------------------
    # ANALISI
    # -------------------------
    st.sidebar.header("3. Analisi")

    metodo = st.sidebar.radio(
        "Trattamento dati:",
        ["Dati Completi", "Filtro Sigma (Gauss)"]
    )

    n_sigma = 2.0
    if metodo == "Filtro Sigma (Gauss)":
        n_sigma = st.sidebar.slider("Sigma", 1.0, 3.0, 2.0, 0.5)

    if not punti:
        st.warning("Seleziona almeno un punto.")
        return

    # =========================
    # LOOP FOGLI
    # =========================
    for punto in punti:

        df = dfs[punto].copy()

        if df.empty or len(df.columns) < 2:
            st.warning(f"{punto} non valido.")
            continue

        # -------------------------
        # DATA COLUMN
        # -------------------------
        col_data = df.columns[0]

        df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
        df = df.dropna(subset=[col_data]).sort_values(col_data)

        st.write(f"## 📍 Punto: {punto}")

        # -------------------------
        # COLONNE NUMERICHE
        # -------------------------
        colonne = []

        for c in df.columns[1:]:
            if "Unnamed" in str(c):
                continue

            if pd.to_numeric(df[c], errors="coerce").notnull().any():
                colonne.append(c)

        if not colonne:
            st.warning("Nessuna colonna numerica valida.")
            continue

        selezionate = st.multiselect(
            f"Sensori {punto}",
            colonne,
            default=[colonne[0]],
            key=punto
        )

        if not selezionate:
            continue

        # -------------------------
        # METRICHE
        # -------------------------
        cols = st.columns(len(selezionate))

        for i, col in enumerate(selezionate):

            serie = pd.to_numeric(df[col], errors="coerce").dropna()

            if serie.empty:
                continue

            cols[i].metric(
                col,
                f"{serie.iloc[-1]:.3f}",
                f"Δ {(serie.max()-serie.min()):.3f}"
            )

        # -------------------------
        # GRAFICO
        # -------------------------
        fig = go.Figure()

        for col in selezionate:

            d = df[[col_data, col]].copy()
            d[col] = pd.to_numeric(d[col], errors="coerce")
            d = d.dropna()

            if d.empty:
                continue

            # =========================
            # FILTRO SIGMA
            # =========================
            if metodo == "Filtro Sigma (Gauss)":
                d[col] = applica_filtro_sigma(d[col], n_sigma)

            d = d.dropna()

            if d.empty:
                continue

            # -------------------------
            # DATI
            # -------------------------
            fig.add_trace(go.Scatter(
                x=d[col_data],
                y=d[col],
                mode="lines+markers",
                name=col
            ))

            # -------------------------
            # TRENDLINE CORRETTA
            # -------------------------
            if len(d) >= 5:

                x = d[col_data].map(pd.Timestamp.toordinal).values
                y = d[col].values

                try:
                    coeff = np.polyfit(x, y, 3)
                    poly = np.poly1d(coeff)

                    fig.add_trace(go.Scatter(
                        x=d[col_data],
                        y=poly(x),
                        mode="lines",
                        name=f"Trend {col}",
                        line=dict(dash="dot", width=2)
                    ))

                except Exception as e:
                    logger.warning(f"Trendline fallita {col}: {e}")

        # -------------------------
        # LAYOUT
        # -------------------------
        fig.update_layout(
            template="plotly_white",
            height=550,
            hovermode="x unified",
            xaxis=dict(
                title="Data",
                tickformat="%d/%m/%Y",
                tickangle=-45
            ),
            yaxis=dict(title="Valore")
        )

        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
