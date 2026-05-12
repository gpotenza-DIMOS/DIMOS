import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import logging
import warnings

from numpy.polynomial.polyutils import RankWarning

# ======================================================
# CONFIGURAZIONE APP
# ======================================================
st.set_page_config(
    page_title="DIMOS - Analisi Topografica",
    layout="wide"
)

warnings.simplefilter("ignore", RankWarning)

# ======================================================
# LOGGER
# ======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("DIMOS")

# ======================================================
# FUNZIONE FILTRO SIGMA
# ======================================================
def applica_filtro_sigma(serie, n_sigma=2.0):

    try:
        serie = pd.to_numeric(serie, errors="coerce")

        media = serie.mean()
        std = serie.std()

        if pd.isna(std) or std == 0:
            return serie

        filtro = (
            (serie >= media - n_sigma * std) &
            (serie <= media + n_sigma * std)
        )

        return serie.where(filtro)

    except Exception as e:
        logger.error(f"Errore filtro sigma: {e}")
        return serie


# ======================================================
# CARICAMENTO EXCEL
# ======================================================
@st.cache_data
def carica_excel(uploaded_file):

    data = {}

    try:

        xl = pd.ExcelFile(uploaded_file, engine="openpyxl")

        for sheet in xl.sheet_names:

            try:

                df = xl.parse(sheet, header=0)

                # rimuove righe completamente vuote
                df = df.dropna(how="all")

                # pulizia colonne
                df.columns = [
                    str(c).strip()
                    for c in df.columns
                ]

                data[sheet] = df

            except Exception as e:
                logger.warning(f"Errore foglio {sheet}: {e}")

        return data

    except Exception as e:
        logger.error(f"Errore caricamento Excel: {e}")
        return {}


# ======================================================
# FUNZIONE CONVERSIONE NUMERICA ROBUSTA
# ======================================================
def converti_numerico(serie):

    return pd.to_numeric(
        serie.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False),
        errors="coerce"
    )


# ======================================================
# MAIN APP
# ======================================================
def main():

    st.title("🛰️ DIMOS - Analisi Topografica Avanzata")

    st.markdown("""
    Applicazione per:
    - lettura file Excel multi-foglio
    - visualizzazione dati topografici
    - trendline automatiche
    - filtro sigma (Gauss)
    """)

    st.markdown("---")

    # ======================================================
    # SIDEBAR - UPLOAD
    # ======================================================
    st.sidebar.header("1️⃣ Caricamento File")

    uploaded_file = st.sidebar.file_uploader(
        "Carica file Excel (.xlsx)",
        type=["xlsx"]
    )

    if uploaded_file is None:
        st.info("Carica un file Excel per iniziare.")
        return

    # ======================================================
    # LETTURA FILE
    # ======================================================
    dfs = carica_excel(uploaded_file)

    if not dfs:
        st.error("Impossibile leggere il file Excel.")
        return

    fogli = list(dfs.keys())

    st.sidebar.success(f"Fogli trovati: {len(fogli)}")

    # ======================================================
    # SELEZIONE PUNTI
    # ======================================================
    st.sidebar.header("2️⃣ Selezione Punti")

    seleziona_tutti = st.sidebar.checkbox(
        "Seleziona tutti i punti"
    )

    if seleziona_tutti:
        punti = fogli
    else:
        punti = st.sidebar.multiselect(
            "Scegli fogli/punti",
            fogli
        )

    if not punti:
        st.warning("Seleziona almeno un punto.")
        return

    # ======================================================
    # FILTRO DATI
    # ======================================================
    st.sidebar.header("3️⃣ Trattamento Dati")

    metodo = st.sidebar.radio(
        "Metodo:",
        [
            "Dati Completi",
            "Filtro Sigma (Gauss)"
        ]
    )

    n_sigma = 2.0

    if metodo == "Filtro Sigma (Gauss)":

        n_sigma = st.sidebar.slider(
            "Valore Sigma",
            min_value=1.0,
            max_value=5.0,
            value=2.0,
            step=0.5
        )

    # ======================================================
    # LOOP PRINCIPALE
    # ======================================================
    for punto in punti:

        st.markdown("---")
        st.subheader(f"📍 Punto: {punto}")

        try:

            df = dfs[punto].copy()

            # ======================================================
            # DEBUG
            # ======================================================
            with st.expander("🔍 Anteprima dati"):

                st.write(df.head())
                st.write(df.dtypes)

            # ======================================================
            # VALIDAZIONE
            # ======================================================
            if df.empty:

                st.warning(f"{punto}: foglio vuoto.")
                continue

            if len(df.columns) < 2:

                st.warning(f"{punto}: numero colonne insufficiente.")
                continue

            # ======================================================
            # COLONNA DATA
            # ======================================================
            col_data = df.columns[0]

            df[col_data] = pd.to_datetime(
                df[col_data],
                errors="coerce",
                dayfirst=True
            )

            df = df.dropna(subset=[col_data])

            if df.empty:

                st.warning(f"{punto}: nessuna data valida.")
                continue

            df = df.sort_values(col_data)

            # ======================================================
            # IDENTIFICAZIONE COLONNE NUMERICHE
            # ======================================================
            colonne_numeriche = []

            for c in df.columns[1:]:

                if "Unnamed" in str(c):
                    continue

                serie_test = converti_numerico(df[c])

                if serie_test.notnull().sum() > 0:
                    colonne_numeriche.append(c)

            if not colonne_numeriche:

                st.warning("Nessuna colonna numerica trovata.")
                continue

            # ======================================================
            # SELEZIONE SENSORI
            # ======================================================
            selezionate = st.multiselect(
                f"Sensori disponibili - {punto}",
                colonne_numeriche,
                default=[colonne_numeriche[0]],
                key=f"sensori_{punto}"
            )

            if len(selezionate) == 0:

                st.warning("Nessun sensore selezionato.")
                continue

            # ======================================================
            # METRICHE
            # ======================================================
            st.markdown("### 📊 Metriche")

            cols_metriche = st.columns(len(selezionate))

            for i, col in enumerate(selezionate):

                serie = converti_numerico(df[col]).dropna()

                if serie.empty:
                    continue

                ultimo = serie.iloc[-1]
                minimo = serie.min()
                massimo = serie.max()
                delta = massimo - minimo

                cols_metriche[i].metric(
                    label=col,
                    value=f"{ultimo:.3f}",
                    delta=f"Range: {delta:.3f}"
                )

                cols_metriche[i].caption(
                    f"Min: {minimo:.3f} | Max: {massimo:.3f}"
                )

            # ======================================================
            # GRAFICO
            # ======================================================
            fig = go.Figure()

            for col in selezionate:

                try:

                    d = df[[col_data, col]].copy()

                    d[col] = converti_numerico(d[col])

                    d = d.dropna()

                    if d.empty:
                        continue

                    # ======================================================
                    # FILTRO SIGMA
                    # ======================================================
                    if metodo == "Filtro Sigma (Gauss)":

                        d[col] = applica_filtro_sigma(
                            d[col],
                            n_sigma
                        )

                    d = d.dropna()

                    if d.empty:
                        continue

                    # ======================================================
                    # GRAFICO PRINCIPALE
                    # ======================================================
                    fig.add_trace(go.Scatter(
                        x=d[col_data],
                        y=d[col],
                        mode="lines+markers",
                        name=col
                    ))

                    # ======================================================
                    # TRENDLINE
                    # ======================================================
                    if len(d) >= 5:

                        try:

                            x = (
                                d[col_data]
                                .astype("int64") // 10**9
                            )

                            y = pd.to_numeric(
                                d[col],
                                errors="coerce"
                            )

                            mask = (
                                np.isfinite(x) &
                                np.isfinite(y)
                            )

                            x = x[mask]
                            y = y[mask]

                            if len(x) >= 5:

                                coeff = np.polyfit(x, y, 3)

                                poly = np.poly1d(coeff)

                                fig.add_trace(go.Scatter(
                                    x=d[col_data],
                                    y=poly(x),
                                    mode="lines",
                                    name=f"Trend {col}",
                                    line=dict(
                                        dash="dot",
                                        width=2
                                    )
                                ))

                        except Exception as e:
                            logger.warning(
                                f"Trendline fallita {col}: {e}"
                            )

                except Exception as e:

                    logger.error(
                        f"Errore elaborazione colonna {col}: {e}"
                    )

            # ======================================================
            # LAYOUT GRAFICO
            # ======================================================
            fig.update_layout(
                template="plotly_white",
                height=600,
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                xaxis=dict(
                    title="Data",
                    tickformat="%d/%m/%Y",
                    tickangle=-45
                ),
                yaxis=dict(
                    title="Valore"
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        except Exception as e:

            st.error(f"Errore nel punto {punto}: {e}")

            logger.exception(e)


# ======================================================
# AVVIO APP
# ======================================================
if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        st.error(f"Errore generale applicazione: {e}")

        logger.exception(e)
