import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re
import os
from io import BytesIO
from datetime import datetime

# --- GESTIONE LIBRERIA WORD ---
try:
    from docx import Document
    from docx.shared import Inches
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# --- LOGICA COLORI VBA ---
def get_vba_color(val):
    v = abs(val)
    if pd.isna(v): return "gray"
    if v <= 1: return "rgb(146, 208, 80)"
    if v <= 2: return "rgb(0, 176, 80)"
    if v <= 3: return "rgb(255, 255, 0)"
    if v <= 4: return "rgb(255, 192, 0)"
    if v <= 5: return "rgb(255, 0, 0)"
    return "rgb(112, 48, 160)"

def run_elettrolivelle():
    st.title("📏 Monitoraggio Elettrolivelle - Sistema ARRAY")
    
    up = st.file_uploader("Carica File Excel (Fabro...)", type=['xlsm', 'xlsx'])
    
    if up:
        xls = pd.ExcelFile(up)
        
        # 1. LETTURA ROBUSTA FOGLIO ARRAY
        if "ARRAY" not in xls.sheet_names:
            st.error("ERRORE: Foglio 'ARRAY' non trovato!")
            return
        
        df_array = pd.read_excel(xls, "ARRAY", header=None)
        # La colonna 0 contiene i nomi delle linee (es. ETS_1, ETS_2...)
        linee_nomi = df_array[0].dropna().unique().tolist()
        
        col_selezione, col_info = st.columns([1, 2])
        with col_selezione:
            sel_linea = st.selectbox("Seleziona Linea da ARRAY", linee_nomi)
        
        # Estraiamo i sensori: prendiamo la riga corrispondente e saltiamo la prima colonna
        riga = df_array[df_array[0] == sel_linea].iloc[0, 1:]
        sequenza_array = riga.dropna().astype(str).tolist()
        
        with col_info:
            st.caption(f"Sequenza rilevata ({len(sequenza_array)} sensori):")
            st.write(" → ".join(sequenza_array))

        # 2. SIDEBAR PARAMETRI
        with st.sidebar:
            st.header("⚙️ Impostazioni")
            asse = st.selectbox("Seleziona Asse", ["X", "Y"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma_val = st.slider("Filtro Gauss (Sigma)", 1.0, 5.0, 2.0)
            limite_y = st.number_input("Limite Grafico +/- (mm)", value=20)
            st.divider()
            mostra_tabella = st.checkbox("Mostra Tabella Dati Elaborati")

        # 3. RICERCA DATI NEI FOGLI ETS_1, ETS_2, etc.
        df_sorgente = None
        for s_name in xls.sheet_names:
            if s_name.startswith("ETS_") and not s_name.endswith(("X", "Y", "C", "P0")):
                temp = pd.read_excel(xls, s_name)
                # Verifichiamo se i sensori della linea sono in questo foglio
                if any(str(sequenza_array[0]) in str(c) for c in temp.columns):
                    df_sorgente = temp
                    break
        
        if df_sorgente is not None:
            time_col = pd.to_datetime(df_sorgente.iloc[:, 0])
            
            # --- ELABORAZIONE DATI ---
            lista_serie = []
            labels_finali = []
            
            for s_id in sequenza_array:
                # Cerchiamo la colonna che contiene l'ID e l'asse
                pattern = rf"{s_id}.*_{asse}"
                match = [c for c in df_sorgente.columns if re.search(pattern, str(c), re.IGNORECASE)]
                
                if match:
                    col_name = match[0]
                    # Conversione Trigonometrica
                    val_rad = np.radians(df_sorgente[col_name].replace(0, np.nan))
                    val_mm = l_barra * np.sin(val_rad)
                    # Delta C0 (Valore - Prima lettura valida)
                    serie_c0 = val_mm - val_mm.iloc[0]
                    
                    # Filtro Gauss
                    m, s = serie_c0.mean(), serie_c0.std()
                    serie_c0 = serie_c0.mask(np.abs(serie_c0 - m) > (s * sigma_val))
                    
                    # Filtro Soglie Hard VBA
                    serie_c0 = serie_c0.mask((serie_c0 > 20) | (serie_c0 < -30))
                    
                    lista_serie.append(serie_c0)
                    labels_finali.append(s_id)
                else:
                    # Se il sensore manca, inseriamo colonna vuota per non rompere la sequenza
                    lista_serie.append(pd.Series([np.nan]*len(df_sorgente)))
                    labels_finali.append(f"{s_id} (Assente)")

            df_finale = pd.concat(lista_serie, axis=1)
            df_finale.columns = labels_finali

            # --- DASHBOARD ---
            tab_grafico, tab_stampe = st.tabs(["📊 Grafico Interattivo", "📝 Generazione Report"])

            with tab_grafico:
                idx = st.slider("Sposta cursore temporale", 0, len(time_col)-1, len(time_col)-1)
                st.write(f"**Data Lettura:** {time_col[idx].strftime('%d/%m/%Y %H:%M:%S')}")
                
                curr_data = df_finale.iloc[idx]
                colors = [get_vba_color(v) for v in curr_data]
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=labels_finali, y=curr_data,
                    mode='lines+markers+text',
                    text=[f"{v:.2f}" if pd.notnull(v) else "" for v in curr_data],
                    textposition="top center",
                    marker=dict(size=12, color=colors, line=dict(width=1, color="black")),
                    line=dict(color="rgba(150,150,150,0.5)", width=2)
                ))
                
                fig.update_layout(
                    yaxis=dict(range=[-limite_y, limite_y], title="Spostamento (mm)"),
                    xaxis=dict(type='category', title="Sequenza Fisica Sensori"),
                    template="plotly_white", height=550
                )
                st.plotly_chart(fig, use_container_width=True)
                
                if mostra_tabella:
                    st.dataframe(df_finale.style.format("{:.2f}").highlight_null(color="red"))

            with tab_stampe:
                if not WORD_AVAILABLE:
                    st.error("Libreria 'python-docx' non installata. Impossibile generare Report.")
                else:
                    st.subheader("Configurazione Report Word")
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        campionamento = st.radio("Seleziona frequenza stampe:", ["Tutti i dati", "Giornaliero", "Settimanale"])
                    
                    if st.button("🚀 GENERA E SCARICA REPORT"):
                        doc = Document()
                        doc.add_heading(f"Report Monitoraggio - Linea {sel_linea}", 0)
                        doc.add_paragraph(f"Asse analizzato: {asse} | Lunghezza barra: {l_barra}mm")
                        
                        # Resampling per non fare 1000 pagine
                        df_report = df_finale.copy()
                        df_report.index = time_col
                        if campionamento == "Giornaliero": df_report = df_report.resample('D').mean().dropna(how='all')
                        elif campionamento == "Settimanale": df_report = df_report.resample('W').mean().dropna(how='all')
                        
                        bar_progress = st.progress(0)
                        for i, (data_rif, row) in enumerate(df_report.iterrows()):
                            # Creazione grafico statico con Matplotlib per Word
                            plt.figure(figsize=(10, 4))
                            plt.plot(labels_finali, row.values, marker='o', color='red', linewidth=1.5)
                            plt.axhline(0, color='black', linewidth=0.5)
                            plt.title(f"Lettura del {data_rif.strftime('%d/%m/%Y')}")
                            plt.ylim(-limite_y, limite_y)
                            plt.xticks(rotation=45)
                            plt.grid(True, alpha=0.3)
                            
                            buf = BytesIO()
                            plt.savefig(buf, format='png', bbox_inches='tight')
                            plt.close()
                            
                            doc.add_heading(f"Data: {data_rif.strftime('%d/%m/%Y')}", level=2)
                            doc.add_picture(buf, width=Inches(6))
                            bar_progress.progress((i+1)/len(df_report))
                        
                        out_word = BytesIO()
                        doc.save(out_word)
                        st.download_button("⬇️ SCARICA FILE WORD", out_word.getvalue(), f"Report_{sel_linea}_{asse}.docx")
        else:
            st.error("Dati non trovati. Assicurati che i nomi in ARRAY corrispondano ai nomi delle colonne nei fogli ETS.")
