import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import os

# --- INIZIALIZZAZIONE SESSIONE (Fondamentale per evitare NameError) ---
if 'anagrafica' not in st.session_state:
    st.session_state.anagrafica = {}
if 'manual_sensors' not in st.session_state:
    st.session_state.manual_sensors = []

def run_app():
    st.sidebar.title("📌 DIMOS Hub")
    menu = st.sidebar.radio("Vai a:", ["Mappe", "Grafici"])
    
    # Caricamento Excel OPZIONALE
    file_input = st.sidebar.file_uploader("Carica Excel (Opzionale)", type=['xlsx', 'xlsm'])

    # Se carichi il file, popoliamo l'anagrafica, altrimenti resta vuota
    if file_input:
        try:
            xls = pd.ExcelFile(file_input)
            if "NAME" in xls.sheet_names:
                df_n = pd.read_excel(xls, sheet_name="NAME", header=None).fillna("nan")
                temp_ana = {}
                for c in range(1, df_n.shape[1]):
                    dl = str(df_n.iloc[0, c]).strip()
                    sn = str(df_n.iloc[1, c]).strip()
                    if dl != "nan":
                        if dl not in temp_ana: temp_ana[dl] = {}
                        temp_ana[dl][sn] = {}
                st.session_state.anagrafica = temp_ana
        except:
            st.sidebar.error("Errore lettura Excel, ma puoi procedere a mano.")

    # --- MODULO MAPPE (LIBERTÀ TOTALE) ---
    if menu == "Mappe":
        st.header("🗺️ Posizionamento Libero Sensori")
        
        c1, c2 = st.columns([1, 3])
        
        with c1:
            st.subheader("✍️ Inserimento Manuale")
            nome_p = st.text_input("Nome Sensore (es. Pippo)", key="p_nome")
            xp = st.number_input("Coordinata X", value=0)
            yp = st.number_input("Coordinata Y", value=0)
            
            if st.button("Inserisci Sensore"):
                if nome_p:
                    st.session_state.manual_sensors.append({'Nome': nome_p, 'X': xp, 'Y': yp})
                    st.success(f"'{nome_p}' aggiunto alla mappa!")

            if st.button("Pulisci Tutto"):
                st.session_state.manual_sensors = []
                st.rerun()

            st.divider()
            img_cad = st.file_uploader("Sfondo: Carica Planimetria/CAD", type=['png', 'jpg', 'jpeg'])

        with c2:
            fig = go.Figure()

            # Gestione Sfondo
            if img_cad:
                img = Image.open(img_cad)
                w, h = img.size
                fig.add_layout_image(dict(
                    source=img, xref="x", yref="y", x=0, y=h, sizex=w, sizey=h,
                    sizing="stretch", layer="below"
                ))
                fig.update_xaxes(range=[0, w], visible=True)
                fig.update_yaxes(range=[0, h], visible=True, scaleanchor="x")
            else:
                # Se non c'è immagine, diamo uno spazio bianco 1000x1000
                fig.update_xaxes(range=[0, 1000], title="X [pixel o m]")
                fig.update_yaxes(range=[0, 1000], title="Y [pixel o m]", scaleanchor="x")
                st.info("Visualizzazione su griglia neutra. Carica un'immagine per lo sfondo CAD.")

            # Visualizzazione Sensori Manuali
            if st.session_state.manual_sensors:
                df_m = pd.DataFrame(st.session_state.manual_sensors)
                fig.add_trace(go.Scatter(
                    x=df_m['X'], y=df_m['Y'],
                    mode='markers+text',
                    text=df_m['Nome'],
                    marker=dict(size=15, color='red', symbol='cross'),
                    textposition="top center",
                    name="Sensori Manuali"
                ))

            fig.update_layout(width=900, height=700, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

    # --- MODULO GRAFICI ---
    elif menu == "Grafici":
        st.header("📈 Visualizzazione Dati")
        if not st.session_state.anagrafica:
            st.warning("Nessun dato Excel caricato. Carica un file per abilitare i grafici.")
        else:
            st.write("Dati anagrafici pronti. Seleziona i sensori per procedere.")

if __name__ == "__main__":
    run_app()
