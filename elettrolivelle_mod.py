import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import os

def ricostruisci_dato_smart(serie, index_attuale, window=50):
    """
    Se il dato è NaN, calcola la media dei dati 'ottimali' nelle ultime N misure.
    """
    if not np.isnan(serie[index_attuale]):
        return serie[index_attuale], False # Dato reale
    
    # Prendi la finestra precedente
    start = max(0, index_attuale - window)
    finestra = serie[start:index_attuale]
    finestra_valida = finestra[~np.isnan(finestra)]
    
    if len(finestra_valida) < 5: # Troppi pochi dati per una media affidabile
        return np.nan, False
    
    # Filtro qualità: media +- deviazione standard
    m = np.mean(finestra_valida)
    s = np.std(finestra_valida)
    dati_ottimali = finestra_valida[(finestra_valida >= m - s) & (finestra_valida <= m + s)]
    
    if len(dati_ottimali) > 0:
        return np.mean(dati_ottimali), True # Dato ricostruito
    return np.nan, False

def run_elettrolivelle():
    # ... (Caricamento file e setup iniziale identico al precedente) ...
    # Assumiamo di avere data_c0 (matrice mm pulita con Gauss)
    
    if up:
        # (Codice parsing ARRAY e selezione foglio...)
        
        # Trasformiamo la matrice in un DataFrame per gestire meglio le finestre temporali
        df_lavoro = pd.DataFrame(data_c0, columns=cols_asse)
        
        # Matrici per il plot finale
        plot_vals = np.zeros_like(data_c0)
        is_ricostruito = np.zeros_like(data_c0, dtype=bool)

        # Applichiamo la logica Smart Interpolation riga per riga (per l'animazione)
        for i in range(len(df_lavoro)):
            for j, col in enumerate(cols_asse):
                val, ric = ricostruisci_dato_smart(df_lavoro[col].values, i)
                plot_vals[i, j] = val
                is_ricostruito[i, j] = ric

        # Seleziona tipo visualizzazione
        tipo_v = st.radio("Modalità:", ["Spostamento Singolo", "Deformata Cumulata"], horizontal=True)
        if "Cumulata" in tipo_v:
            # La somma cumulata ora userà i dati ricostruiti, evitando interruzioni
            plot_vals = np.nancumsum(plot_vals, axis=1)

        # --- COSTRUZIONE GRAFICO CON DOPPIO MARKER ---
        fig = go.Figure()
        
        # Iteriamo sui sensori per il frame 0 (necessario per definire gli stili)
        for j in range(len(cols_asse)):
            marker_style = "circle" if not is_ricostruito[0, j] else "square"
            marker_color = "red" if not is_ricostruito[0, j] else "blue"
            marker_symbol = "!" if is_ricostruito[0, j] else "" # Testo sovrapposto opzionale
            
            # Nota: Per Plotly animato è più efficiente usare una traccia unica, 
            # ma per avere simboli diversi dobbiamo gestire i vettori di simboli
            
        symbols = ["circle" if not r else "square" for r in is_ricostruito[0]]
        colors = ["red" if not r else "#00b4d8" for r in is_ricostruito[0]]
        
        fig.add_trace(go.Scatter(
            x=ids_grafico, y=plot_vals[0],
            mode='lines+markers+text',
            text=[f"!" if r else "" for r in is_ricostruito[0]], # Punto esclamativo per i ricostruiti
            textposition="middle center",
            textfont=dict(color="white", size=10, family="Arial Black"),
            marker=dict(
                size=14, 
                symbol=symbols, 
                color=colors,
                line=dict(width=2, color="yellow" if any(is_ricostruito[0]) else "white")
            ),
            line=dict(width=3, color='#1f77b4'),
            connectgaps=True # Ora possiamo connettere perché i buchi sono tappati dalla media!
        ))

        # Frames dell'animazione aggiornati con i simboli dinamici
        frames = []
        for i in range(len(plot_vals)):
            current_symbols = ["circle" if not r else "square" for r in is_ricostruito[i]]
            current_colors = ["red" if not r else "#00b4d8" for r in is_ricostruito[i]]
            frames.append(go.Frame(
                data=[go.Scatter(
                    y=plot_vals[i],
                    marker=dict(symbol=current_symbols, color=current_colors),
                    text=[f"!" if r else "" for r in is_ricostruito[i]]
                )],
                name=str(i)
            ))
        
        fig.frames = frames
        # ... (Resto del layout e animazione) ...
        st.plotly_chart(fig, use_container_width=True)
