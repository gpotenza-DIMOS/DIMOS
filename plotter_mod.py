import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def main():
    st.title("📈 Visualizzatore Universale")

    # --- CARICAMENTO FILE ---
    uploaded_file = st.file_uploader("Carica un file (CSV o Excel)", type=["csv", "xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Identifica l'estensione e carica i dati
            if uploaded_file.name.endswith('.csv'):
                # Prova prima col punto e virgola, poi con la virgola
                try:
                    df = pd.read_csv(uploaded_file, sep=';')
                    if len(df.columns) <= 1: raise Exception()
                except:
                    df = pd.read_csv(uploaded_file, sep=',')
            else:
                df = pd.read_excel(uploaded_file)

            st.success(f"File '{uploaded_file.name}' caricato con successo!")

            # --- SELEZIONE COLONNE ---
            col1, col2 = st.columns(2)
            
            with col1:
                colonna_tempo = st.selectbox("Seleziona la colonna del Tempo/Data", df.columns)
            
            with col2:
                colonne_dati = st.multiselect("Seleziona i sensori da visualizzare", 
                                             [c for c in df.columns if c != colonna_tempo])

            if colonna_tempo and colonne_dati:
                # Convertiamo il tempo in formato datetime se possibile
                df[colonna_tempo] = pd.to_datetime(df[colonna_tempo], errors='ignore')
                
                # --- CREAZIONE GRAFICO ---
                fig = go.Figure()
                for col in colonne_dati:
                    fig.add_trace(go.Scatter(x=df[colonna_tempo], y=df[col], name=col, mode='lines+markers'))

                fig.update_layout(
                    template="plotly_white",
                    hovermode="x unified",
                    xaxis_title=colonna_tempo,
                    yaxis_title="Valore"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Anteprima dati
                with st.expander("Visualizza Tabella Dati"):
                    st.dataframe(df)

        except Exception as e:
            st.error(f"Errore durante la lettura del file: {e}")
    else:
        st.info("In attesa del caricamento di un file...")

if __name__ == "__main__":
    main()
