import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO

# --- GESTIONE LIBRERIA STAMPA ---
try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- LOGICA SMART INTERPOLATION (MEDIA MOVIBILE + SIGMA) ---
def ricostruisci_dato_smart(serie, index_attuale, window=50):
    if not np.isnan(serie[index_attuale]):
        return serie[index_attuale], False
    
    start = max(0, index_attuale - window)
    finestra = serie[start:index_attuale]
    finestra_valida = finestra[~np.isnan(finestra)]
    
    if len(finestra_valida) < 5:
        return np.nan, False
    
    m = np.mean(finestra_valida)
    s = np.std(finestra_valida)
    dati_ottimali = finestra_valida[(finestra_valida >= m - s) & (finestra_valida <= m + s)]
    
    if len(dati_ottimali) > 0:
        return np.mean(dati_ottimali), True
    return np.nan, False

def run_elettrolivelle():
    # --- LOGO E INTESTAZIONE ---
    if os.path.exists("logo_dimos.jpg"):
        st.image("logo_dimos.jpg", width=400)
    
    st.title("📏 Monitoraggio Avanzato Elettrolivelle")
    st.markdown("---")

    # --- CARICAMENTO FILE IN PAGINA PRINCIPALE ---
    up = st.file_uploader("📂 Carica file Excel (Sezioni + ARRAY)", type=['xlsx', 'xlsm'], key="up_livelle_main")
    
    if up:
        xls = pd.ExcelFile(up)
        
        # Lettura Sequenza ARRAY
        sequenza_fisica = None
        if "ARRAY" in xls.sheet_names:
            df_array = pd.read_excel(xls, sheet_name="ARRAY")
            sequenza_fisica = df_array.iloc[:, 0].dropna().astype(str).tolist()

        sheets = [s for s in xls.sheet_names if s not in ["ARRAY", "NAME", "Info"]]
        sel_sheet = st.selectbox("Seleziona Layer / Sezione di monitoraggio:", sheets)
        
        # --- SIDEBAR PER PARAMETRI TECNICI ---
        with st.sidebar:
            st.header("⚙️ Configurazione")
            asse = st.selectbox("Asse di Analisi", ["X", "Y", "Z"])
            l_barra = st.number_input("Lunghezza Barra (mm)", value=3000)
            sigma_val = st.slider("Filtro Gauss (Sigma)", 0.0, 5.0, 2.5)
            st.divider()
            st.header("🎬 Animazione")
            vel = st.slider("Velocità (ms)", 50, 1000, 200)
            limite_y = st.number_input("Range Y (+/- mm)", value=20.0)

        # --- CARICAMENTO DATI ---
        df = pd.read_excel(up, sheet_name=sel_sheet)
        time_col = pd.to_datetime(df.iloc[:, 0])
        cols_asse = [c for c in df.columns if f"_{asse}" in str(c)]
        
        # Ordinamento secondo ARRAY
        if sequenza_fisica:
            def sort_key(c):
                for i, s in enumerate(sequenza_fisica):
                    if s in c: return i
                return 999
            cols_asse = sorted(cols_asse, key=sort_key)

        if cols_asse:
            # --- ELABORAZIONE MATEMATICA VETTORIALIZZATA ---
            raw_values = df[cols_asse].replace(0, np.nan).values
            data_mm = l_barra * np.sin(np.radians(raw_values))
            # Delta C0 (riferito alla prima riga)
            data_c0 = data_mm - np.nanmean(data_mm[0:1, :], axis=0)

            # Filtro Gauss (Pulizia)
            if sigma_val > 0:
                m_vec = np.nanmean(data_c0, axis=0)
                s_vec = np.nanstd(data_c0, axis=0)
                data_c0[(data_c0 < m_vec - sigma_val*s_vec) | (data_c0 > m_vec + sigma_val*s_vec)] = np.nan

            # --- SMART INTERPOLATION ---
            plot_vals = np.zeros_like(data_c0)
            is_ricostruito = np.zeros_like(data_c0, dtype=bool)
            for j in range(len(cols_asse)):
                for i in range(len(data_c0)):
                    val, ric = ricostruisci_dato_smart(data_c0[:, j], i)
                    plot_vals[i, j] = val
                    is_ricostruito[i, j] = ric

            # --- VISUALIZZAZIONE ---
            tab_din, tab_rep = st.tabs(["🎬 Deformata Dinamica", "📄 Report e Export"])

            with tab_din:
                tipo_v = st.radio("Visualizzazione:", ["Spostamento Singolo", "Deformata Cumulata"], horizontal=True)
                if "Cumulata" in tipo_v:
                    final_plot = np.nancumsum(plot_vals, axis=1)
                else:
                    final_plot = plot_vals

                ids = [re.search(r'CL_(\d+)', c).group(1) if "CL_" in c else c for c in cols_asse]
                
                fig = go.Figure()
                fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3)

                # Setup Frame 0 con Pallini/Quadrati
                symbols = ["circle" if not r else "square" for r in is_ricostruito[0]]
                colors = ["red" if not r else "#00b4d8" for r in is_ricostruito[0]]
                
                fig.add_trace(go.Scatter(
                    x=ids, y=final_plot[0], mode='lines+markers+text',
                    text=[f"!" if r else "" for r in is_ricostruito[0]],
                    textposition="middle center", textfont=dict(color="white", size=10),
                    marker=dict(size=14, symbol=symbols, color=colors, line=dict(width=2, color="white")),
                    line=dict(width=3, color='#1f77b4'), connectgaps=True
                ))

                frames = [go.Frame(data=[go.Scatter(
                    y=final_plot[i],
                    marker=dict(symbol=["circle" if not r else "square" for r in is_ricostruito[i]],
                                color=["red" if not r else "#00b4d8" for r in is_ricostruito[i]]),
                    text=[f"!" if r else "" for r in is_ricostruito[i]]
                )], name=str(i)) for i in range(len(final_plot))]
                
                fig.frames = frames
                fig.update_layout(
                    yaxis=dict(range=[-limite_y, limite_y], title="Spostamento (mm)"),
                    template="plotly_white", height=600,
                    updatemenus=[{"buttons": [{"args": [None, {"frame": {"duration": vel}}], "label": "▶ Play", "method": "animate"},
                                              {"args": [[None], {"frame": {"duration": 0}}], "label": "⏸ Pausa", "method": "animate"}],
                                  "type": "buttons", "showactive": False, "x": 0.05, "y": 1.15}],
                    sliders=[{"steps": [{"method": "animate", "label": time_col[i].strftime("%H:%M"), "args": [[str(i)], {"frame": {"duration": vel}}]} for i in range(len(final_plot))]}]
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab_rep:
                # --- STAMPA WORD (FUNZIONANTE) ---
                if st.button("🚀 GENERA REPORT WORD (.docx)"):
                    if DOCX_AVAILABLE:
                        doc = Document()
                        doc.add_heading(f'Report Elettrolivelle - {sel_sheet}', 0)
                        
                        # Grafico Deformata Finale
                        plt.figure(figsize=(10, 5))
                        plt.plot(ids, final_plot[-1], marker='o', color='red', label='Ultima Lettura')
                        plt.axhline(0, color='black', lw=1)
                        plt.title(f"Deformata Finale - Asse {asse}")
                        plt.grid(True)
                        
                        buf = BytesIO()
                        plt.savefig(buf, format='png')
                        plt.close()
                        doc.add_picture(buf, width=Inches(6))
                        
                        doc.add_paragraph(f"\nParametri: Barra {l_barra}mm, Sigma {sigma_val}")
                        
                        out = BytesIO()
                        doc.save(out)
                        st.download_button("⬇️ SCARICA DOCUMENTO", out.getvalue(), f"Report_{sel_sheet}.docx")
                    else:
                        st.error("Libreria docx non trovata.")

    else:
        st.info("👋 Benvenuto! Carica un file Excel per iniziare l'analisi delle elettrolivelle.")
