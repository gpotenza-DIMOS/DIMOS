import streamlit as st
import pandas as pd
import json
import os
import requests
import folium
from folium.features import DivIcon
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
from io import BytesIO
import base64
import xlrd  # Necessario per xlsm
import re

CONFIG_FILE = "mac_positions.json"

# Impostazione della pagina a layout ampio
st.set_page_config(layout="wide")

# ----------------- UTILS & I/O -----------------
def load_positions():
    """Carica le posizioni salvate dal file JSON."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Errore durante il caricamento di {CONFIG_FILE}: {e}")
            return {}
    return {}

def save_positions(data):
    """Salva le posizioni dei sensori nel file JSON."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Errore durante il salvataggio di {CONFIG_FILE}: {e}")

def get_coords(city_name):
    """Utilizza Nominatim per ottenere le coordinate di una città."""
    if not city_name: return None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'DIMOS_MAC_DASHBOARD_V2'}
        res = requests.get(url, headers=headers).json()
        if res:
            return float(res[0]['lat']), float(res[0]['lon'])
    except Exception:
        return None
    return None

def parse_web_name(web_name):
    """Parsifica il nome web (es. 'CO_9277 CL_01_X [°]') per estrarre Datalogger, Sensore, Parametro e Unità."""
    datalogger = None
    sensor_id = None
    parameter = None
    unit = None
    
    # Cerchiamo il pattern [unità]
    unit_match = re.search(r'\[(.*?)\]', web_name)
    if unit_match:
        unit = unit_match.group(1)
        # Rimuoviamo l'unità dal nome per pulirlo
        name_clean = re.sub(r'\[(.*?)\]', '', web_name).strip()
    else:
        name_clean = web_name.strip()
        unit = "N.A."
        
    parts = name_clean.split(' ')
    if len(parts) >= 2:
        datalogger = parts[0] # es CO_XXXX
        
        sensor_part = parts[1] # es. VAR5 o CL_01_X
        # Controlliamo se ci sono dei separatori nel nome del sensore
        sensor_parts = sensor_part.split('_')
        
        if len(sensor_parts) == 1:
            # Caso semplice (es. VAR5)
            sensor_id = sensor_part
            parameter = "Dato" # Nome di default se c'è una sola grandezza
        elif len(sensor_parts) >= 2:
            # Caso multisensore (es. CL_01_X)
            # Prendiamo tutto tranne l'ultimo elemento come ID sensore
            sensor_id = "_".join(sensor_parts[:-1]) # es CL_01
            # L'ultimo elemento è il parametro
            parameter = sensor_parts[-1] # es. X, T1...
    else:
        datalogger = "Sconosciuto"
        sensor_id = web_name
        parameter = "Dato"
        unit = "N.A."

    return datalogger, sensor_id, parameter, unit

# ----------------- PARSING EXCEL AVANZATO -----------------
def parse_excel_advanced(file_uploader_obj):
    """
    Legge il file Excel (xlsx/xlsm) per estrarre l'anagrafica dei sensori,
    le coordinate e i parametri misurati.
    """
    try:
        # Leggiamo il file come un oggetto ExcelFile per accedere ai fogli
        xls = pd.ExcelFile(file_uploader_obj)
    except Exception as e:
        st.error(f"Impossibile aprire il file Excel: {e}")
        return None

    anagrafica = {} # Struttura: {Datalogger: {Sensore: { 'parameters': {Nome_Parametro: Unità}, 'coords': (lat, lon) }}}

    if "NAME" in xls.sheet_names:
        st.info("Foglio 'NAME' trovato, parsing in corso...")
        # Leggiamo il foglio NAME
        df_name = pd.read_excel(xls, sheet_name="NAME", header=None)
        # Riempiamo i valori NaN per evitare errori di conversione a stringa
        df_name = df_name.fillna("")
        
        # Saltiamo la colonna A (indici). Scansioniamo le colonne dalla B in poi.
        for col_idx in range(1, df_name.shape[1]):
            # Riga 1: Nome Datalogger
            dl = str(df_name.iloc[0, col_idx]).strip()
            # Riga 2: Nome Sensore
            sn = str(df_name.iloc[1, col_idx]).strip()
            # Riga 3: Nome Web (per ricavare parametri e unità)
            wn = str(df_name.iloc[2, col_idx]).strip()
            # Riga 4, 5: Lat, Lon
            try:
                lat_str = str(df_name.iloc[3, col_idx]).strip()
                lon_str = str(df_name.iloc[4, col_idx]).strip()
                
                lat = float(lat_str) if lat_str and lat_str.lower() != 'nan' else None
                lon = float(lon_str) if lon_str and lon_str.lower() != 'nan' else None
            except:
                lat, lon = None, None

            # Se mancano Datalogger o Sensore, non procediamo per questa colonna
            if not dl or not sn: continue

            # Parsifichiamo il Nome Web per estrarre il parametro
            _, _, parameter, unit = parse_web_name(wn)
            
            if dl not in anagrafica:
                anagrafica[dl] = {}
            if sn not in anagrafica[dl]:
                anagrafica[dl][sn] = {'parameters': {}, 'coords': (lat, lon)}
            
            # Aggiungiamo il parametro con la sua unità
            # (anche se il parametro è lo stesso, sovrascriverà, ma è lo stesso sensore)
            # Aggiungiamo il Nome Web completo come chiave del parametro per identificarlo
            anagrafica[dl][sn]['parameters'][wn] = unit

    else:
        # st.warning("Foglio 'NAME' non trovato, parsing dai fogli dati (CO_XXXX VARX)...")
        # # Tentiamo di fare il parsing dai fogli dati (CO_...)
        # data_sheets = [s for s in xls.sheet_names if s.startswith("CO_")]
        
        # if not data_sheets:
        #     st.error("Nessun foglio 'NAME' e nessun foglio 'CO_...' trovato nel file.")
        #     return None
        st.error("Nessun foglio 'NAME' trovato nel file.")
        return None
        
        # # Implementazione base per parsing dai fogli dati
        # for sheet_name in data_sheets:
        #     # Leggiamo il foglio per intero per trovare i nomi web nelle intestazioni
        #     # Assumiamo che la riga 3 (header in pandas) contenga i nomi web.
        #     # Leggiamo solo le prime righe per velocizzare
        #     try:
        #         df_data_head = pd.read_excel(xls, sheet_name=sheet_name, header=2, nrows=0)
        #     except: continue
                
        #     web_names = [col for col in df_data_head.columns if '[' in str(col) and ']' in str(col)]
            
        #     for wn in web_names:
        #         dl, sn, parameter, unit = parse_web_name(wn)
                
        #         if not dl or not sn: continue

        #         if dl not in anagrafica:
        #             anagrafica[dl] = {}
        #         if sn not in anagrafica[dl]:
        #             # Nessuna coordinata disponibile se mancano il foglio NAME
        #             anagrafica[dl][sn] = {'parameters': {}, 'coords': (None, None)}
                
        #         # Aggiungiamo il parametro con la sua unità
        #         anagrafica[dl][sn]['parameters'][wn] = unit

    return anagrafica

# ----------------- MAIN -----------------
def run_map_manager():
    st.title("🌍 Dashboard MAC Interattiva Avanzata")

    # Inizializzazione Session State
    if 'coords_from_click' not in st.session_state: st.session_state.coords_from_click = (None, None)
    if 'current_map_center' not in st.session_state: st.session_state.current_map_center = [45.4642, 9.1900] # Milano
    if 'marker_shape' not in st.session_state: st.session_state.marker_shape = 'square'
    if 'marker_color' not in st.session_state: st.session_state.marker_color = 'blue'

    # Caricamento Posizioni Salvanate
    positions = load_positions()

    # ============================== SIDEBAR: GESTIONE DATI ==============================
    with st.sidebar:
        st.header("⚙️ Configurazione Dati")
        
        # ---------- 1. GESTIONE EXCEL ----------
        with st.expander("📂 Carica o Cambia Excel", expanded='anagrafica_completa' not in st.session_state):
            file_input = st.file_uploader("Carica Excel (Foglio NAME)", type=['xlsx', 'xlsm'])
            if file_input:
                # Eseguiamo il parsing avanzato
                ana = parse_excel_advanced(file_input)
                if ana:
                    st.session_state['anagrafica_completa'] = ana
                    
                    # Uniamo l'anagrafica appena letta con le posizioni JSON esistenti
                    # Se un sensore dell'Excel ha coordinate, le usiamo per aggiornare il JSON
                    # se quel sensore non è già nel JSON con coordinate valide.
                    new_positions_found = 0
                    for dl, sensors in ana.items():
                        for sn, data in sensors.items():
                            key = f"{dl} | {sn}"
                            lat_excel, lon_excel = data['coords']
                            
                            # Se abbiamo trovato coordinate nell'Excel e il sensore non è già salvato con coordinate
                            if lat_excel is not None and lon_excel is not None:
                                if key not in positions:
                                    positions[key] = {"nome": sn, "lat": lat_excel, "lon": lon_excel, "dl": dl}
                                    new_positions_found += 1
                                elif (positions[key]['lat'] is None or positions[key]['lon'] is None):
                                    positions[key]['lat'] = lat_excel
                                    positions[key]['lon'] = lon_excel
                                    new_positions_found += 1
                    
                    if new_positions_found > 0:
                        save_positions(positions)
                        st.info(f"Aggiornate {new_positions_found} posizioni da Excel.")

                    st.success("Excel caricato e anagrafica aggiornata.")
                else:
                    st.error("Impossibile leggere l'anagrafica dall'Excel.")
            
            if 'anagrafica_completa' in st.session_state:
                if st.button("🔄 Cancella Dati Excel in Sessione"):
                    for k in ['anagrafica_completa']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()

        # ---------- 2. CONTROLLO VISUALIZZAZIONE E SELEZIONE PARAMETRI ----------
        if 'anagrafica_completa' in st.session_state:
            st.markdown("---")
            st.header("📊 Filtro Monitoraggio")
            ana = st.session_state['anagrafica_completa']
            
            # Selezione Datalogger
            dataloggers = sorted(list(ana.keys()))
            sel_dl = st.selectbox("1. Seleziona Datalogger (per Monitoraggio)", ["Nessun Datalogger selezionato"] + dataloggers)
            
            if sel_dl != "Nessun Datalogger selezionato":
                # Selezione Sensori del datalogger selezionato
                sensors = sorted(list(ana[sel_dl].keys()))
                sel_sn = st.selectbox(f"2. Seleziona Sensore di {sel_dl}", ["Nessun Sensore selezionato"] + sensors)
                
                if sel_sn != "Nessun Sensore selezionato":
                    # Selezione Parametri (Grandezze Fisiche) del sensore selezionato
                    parameters_wn_dict = ana[sel_dl][sel_sn]['parameters'] # Dict {Nome_Web: Unità}
                    
                    st.markdown(f"**Grandezze Fisiche disponibili per {sel_sn}:**")
                    selected_params = []
                    
                    for wn, unit in parameters_wn_dict.items():
                        # Mostriamo il nome parametro o parte del Nome Web e l'unità
                        # estraiamo il parametro dal web name per visualizzarlo meglio
                        _, _, parameter_name, unit_check = parse_web_name(wn)
                        # Creiamo una label leggibile
                        label = f"{parameter_name} [{unit}]" # es. X [°], T1 [°C], VAR5 [mm]
                        
                        if st.checkbox(label, key=f"check_{wn}"):
                            # Se selezionato, memorizziamo il Nome Web completo (chiave univoca)
                            selected_params.append(wn)
                            
                    if selected_params:
                        # Nota: qui non facciamo nulla, ma selected_params è disponibile
                        # per essere usato in un grafico o tabella separati.
                        # st.success(f"{len(selected_params)} parametri selezionati per il monitoraggio.")
                        # st.write(selected_params) # debug
                        pass
        
        # ---------- 3. INSERIMENTO/MODIFICA MANUALE POSIZIONI ----------
        st.markdown("---")
        st.header("📍 Inserimento Manuale Posizione")
        st.markdown("Compila i campi sotto. Puoi cliccare sulla mappa per riempire automaticamente Latitudine e Longitudine.")
        
        man_dl = st.text_input("Nome Datalogger (manuale)", key="man_dl")
        man_sn = st.text_input("Nome Sensore (manuale)", key="man_sn")
        
        lat_from_state, lon_from_state = st.session_state.coords_from_click
        man_lat = st.number_input("Latitudine", value=lat_from_state if lat_from_state is not None else 0.0, format="%.6f", key="man_lat")
        man_lon = st.number_input("Longitudine", value=lon_from_state if lon_from_state is not None else 0.0, format="%.6f", key="man_lon")
        
        if st.button("➕ Salva/Aggiorna Posizione sulla Mappa"):
            if man_dl and man_sn and man_lat and man_lon:
                man_dl = man_dl.strip()
                man_sn = man_sn.strip()
                key = f"{man_dl} | {man_sn}"
                
                # Creiamo l'oggetto posizione
                positions[key] = {"nome": man_sn, "lat": man_lat, "lon": man_lon, "dl": man_dl}
                
                # Se abbiamo anche l'anagrafica Excel caricata, controlliamo se questo sensore
                # manuale è tra quelli riconosciuti dall'Excel.
                if 'anagrafica_completa' in st.session_state:
                    if man_dl not in st.session_state['anagrafica_completa'] or man_sn not in st.session_state['anagrafica_completa'][man_dl]:
                        st.warning(f"Nota: il sensore '{key}' salvato non corrisponde a nessun sensore definito nell'anagrafica Excel. Sarà mostrato sulla mappa ma non avrà parametri per il monitoraggio.")
                    # else:
                    #     # Se corrisponde, aggiorniamo le coordinate anche nell'anagrafica in sessione
                    #     st.session_state['anagrafica_completa'][man_dl][man_sn]['coords'] = (man_lat, man_lon)
                
                save_positions(positions)
                # Reset coordinate da click dopo il salvataggio
                st.session_state.coords_from_click = (None, None)
                st.success(f"Posizione per '{key}' salvata con successo!")
                st.rerun()
            else:
                st.error("Tutti i campi (Datalogger, Sensore, Lat, Lon) sono obbligatori per il salvataggio manuale.")

        st.markdown("---")
        st.header("🗑️ Reset Mappa")
        if st.button("🗑️ Cancella TUTTI i Marker salvati (JSON)"):
             save_positions({})
             st.rerun()

    # ============================== AREA PRINCIPALE: CONTROLLI MAPPA ==============================
    col_map_1, col_map_2, col_map_3 = st.columns([1,1,2])
    
    with col_map_1:
        # ---------- 4. OVERLAY PLANIMETRIA ----------
        with st.expander("🖼️ Overlay Planimetria"):
            up_img = st.file_uploader("Carica immagine", type=['png','jpg','jpeg'])
            scale_slider = st.slider("Scala", 0.0001, 0.02, 0.002, 0.0001)
            rotation_slider = st.slider("Rotazione (°)", -180, 180, 0)
            opacity_slider = st.slider("Trasparenza", 0.0, 1.0, 0.5)

    with col_map_2:
        # ---------- 5. STILE MARKER ----------
        with st.expander("🎨 Stile Marker"):
            # st.markdown("##### Forma")
            shape_opts = {'quadrato': 'square', 'cerchio': 'circle', 'stella': 'star', 'triangolo (up)': 'triangle-up'}
            sel_shape_label = st.selectbox("Forma", list(shape_opts.keys()), index=0)
            st.session_state.marker_shape = shape_opts[sel_shape_label]
            
            # st.markdown("##### Colore")
            color_opts = ['blue', 'red', 'green', 'orange', 'purple', 'black']
            st.session_state.marker_color = st.selectbox("Colore", color_opts, index=0)
            

    with col_map_3:
        # ---------- 6. CENTRO MAPPA / RICERCA ----------
        # if 'center' not in st.session_state:
        #     st.session_state.center = [45.4642, 9.1900] # Milano

        city = st.text_input("🔍 Cerca città", key="city_search", help="Scrivi il nome di una città e premi Invio per spostare la mappa")
        if city:
            coords = get_coords(city)
            if coords:
                st.session_state.current_map_center = coords
                # Forziamo il rerun per aggiornare la mappa
                st.rerun()
                st.success(f"Mappa spostata su: {city}")

    # ============================== CREAZIONE MAPPA ==============================
    # Creiamo la mappa Folium
    m = folium.Map(location=st.session_state.current_map_center, zoom_start=18)
    # Aggiungiamo il controllo per le coordinate al mouse
    folium.LatLngPopup().add_to(m)

    # ---------- 7. APPLICA OVERLAY PLANIMETRIA ----------
    if up_img:
        try:
            from PIL import Image
            img = Image.open(up_img).convert("RGBA")
            w, h = img.size
            aspect_ratio = h / w
            if rotation_slider != 0:
                img = img.rotate(-rotation_slider, expand=True)
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64_img = base64.b64encode(buf.getvalue()).decode()

            lat, lon = st.session_state.current_map_center
            height = scale_slider * aspect_ratio
            # Bounds: [[sud, ovest], [nord, est]]
            bounds = [[lat - height, lon - scale_slider], [lat + height, lon + scale_slider]]

            overlay = ImageOverlay(image=f"data:image/png;base64,{b64_img}", bounds=bounds, opacity=opacity_slider)
            overlay.add_to(m)
        except Exception as e:
            st.error(f"Errore durante l'applicazione dell'overlay: {e}")

    # ---------- 8. APPLICA MARKER (SENSORI SALVATI) ----------
    # Leggiamo lo stile memorizzato in session state
    marker_shape = st.session_state.marker_shape
    marker_color = st.session_state.marker_color
    
    # HTML personalizzato per il marker (forma e testo interno)
    # Utilizziamo delle classi CSS inline per definire la forma e il colore.
    # DivIcon non supporta nativamente le forme folium.Icon.
    
    border_radius = "0%" # default quadrato
    if marker_shape == 'circle':
        border_radius = "50%"
    elif marker_shape == 'star':
        # Approssimazione star con clip-path
        border_radius = "0%"
        # clip_path = "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)"
    else:
        border_radius = "0%" # square o altro

    for key, p in positions.items():
        if p['lat'] is not None and p['lon'] is not None:
            dl_p = p.get('dl', 'N.A.')
            sn_p = p.get('nome', 'N.A.')
            
            tooltip_text = f"Datalogger: {dl_p}<br>Sensore: {sn_p}"
            
            # Creazione DivIcon HTML
            icon_html = f"""
                <div style="
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    width: 40px;
                    height: 40px;
                    background-color: {marker_color};
                    border: 2px solid white;
                    border-radius: {border_radius};
                    color: white;
                    font-weight: bold;
                    font-size: 10px;
                    text-align: center;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
                    ">
                    {sn_p[:5]} # Mostriamo i primi 5 caratteri del sensore
                </div>
            """
            
            folium.Marker(
                [p['lat'], p['lon']],
                icon=DivIcon(
                    icon_size=(40,40),
                    icon_anchor=(20,20), # Centrato sul punto
                    html=icon_html
                ),
                tooltip=folium.Tooltip(tooltip_text)
            ).add_to(m)

    # ============================== RENDER MAPPA E INTERAZIONE ==============================
    # Rendering della mappa. Restituisce le informazioni sull'interazione (click, ecc.)
    output = st_folium(m, width="100%", height=650)

    # ---------- 9. GESTIONE CLICK SULLA MAPPA ----------
    if output.get("last_clicked"):
        lat_c = output["last_clicked"]["lat"]
        lon_c = output["last_clicked"]["lng"]
        
        # Salviamo le coordinate cliccate nel session state per l'inserimento manuale
        st.session_state.coords_from_click = (lat_c, lon_c)
        st.info(f"Punto cliccato: Lat {lat_c:.6f}, Lon {lon_c:.6f}. Coordinate copiate nella sidebar!")
        # Forziamo un rerun per aggiornare i campi numerici nella sidebar
        st.rerun()

    # ============================== VISUALIZZAZIONE TABELLA DATI ==============================
    if positions:
        with st.expander("📄 Tabella Posizioni Sensori (JSON)"):
            # Convertiamo il dizionario in DataFrame per una migliore visualizzazione
            df_pos = pd.DataFrame.from_dict(positions, orient='index').reset_index(drop=True)
            st.dataframe(df_pos)

if __name__ == "__main__":
    run_map_manager()
