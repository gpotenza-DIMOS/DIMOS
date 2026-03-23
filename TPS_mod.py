# TPS_mod.py
import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

class SokkiaIXController:
    """Controller per Sokkia iX-1200 con Algoritmo Topografico Integrato"""
    def __init__(self, port, baudrate=38400, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.laser_on = False
        self.face = 1
        self.last_measure = None
        self.connect()

    def connect(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            self.ser.write(b"\r\n") # Wake up call
            st.success(f"✅ Connesso a {self.port} @ {self.baudrate} baud")
        except Exception as e:
            st.error(f"❌ Errore connessione: {e}")
            self.ser = None

    def _send_command(self, command):
        if not self.ser or not self.ser.is_open:
            st.warning("Strumento non connesso.")
            return None
        try:
            self.ser.reset_input_buffer()
            self.ser.write(f"00{command}\r\n".encode('ascii'))
            time.sleep(0.2)
            response = self.ser.readline().decode('ascii').strip()
            return response
        except Exception as e:
            st.error(f"Errore comunicazione: {e}")
            return None

    def process_data(self, raw, h_instr=1.50, h_reflector=1.50):
        """Algoritmo matematico per trasformare stringa grezza in coordinate"""
        if not raw or len(raw) < 15:
            return None
        matches = re.findall(r'[+-]?\d+', raw)
        if len(matches) < 3:
            return {"Errore": "Formato stringa non riconosciuto", "Raw": raw}
        try:
            hz_deg = float(matches[0]) / 100000
            v_deg = float(matches[1]) / 100000
            sd = float(matches[2]) / 1000
            hz_rad = math.radians(hz_deg)
            v_rad = math.radians(v_deg)
            hd = sd * math.sin(v_rad)
            dN = hd * math.cos(hz_rad)
            dE = hd * math.sin(hz_rad)
            dZ = (sd * math.cos(v_rad)) + h_instr - h_reflector
            self.last_measure = {
                "Angolo Hz": f"{hz_deg:.4f}°",
                "Angolo V": f"{v_deg:.4f}°",
                "Dist. Inclinata": f"{sd:.3f} m",
                "Dist. Orizzontale": f"{hd:.3f} m",
                "Delta Nord (Y)": f"{dN:.3f} m",
                "Delta Est (X)": f"{dE:.3f} m",
                "Delta Quota (Z)": f"{dZ:.3f} m"
            }
            return self.last_measure
        except Exception as e:
            return {"Errore": str(e), "Raw": raw}

    # --- Comandi originali ---
    def change_face(self, position=1):
        self.face = position
        cmd = "P1" if position == 1 else "P2"
        return self._send_command(cmd)

    def laser_pointer(self, state=True):
        self.laser_on = state
        cmd = "L1" if state else "L0"
        return self._send_command(cmd)

    def power_off(self):
        return self._send_command("PW0")

# --- INTERFACCIA STREAMLIT CON MONITORAGGIO ---
def run_tps_monitoring(auto_refresh=False):
    st.set_page_config(page_title="Sokkia iX-1200 Controller", layout="wide")
    st.title("🛰️ TPS Monitoring - Sokkia iX-1200")

    st.sidebar.header("Parametri di Calcolo")
    h_i = st.sidebar.number_input("Altezza Strumento (m)", value=1.500, format="%.3f")
    h_p = st.sidebar.number_input("Altezza Prisma (m)", value=1.500, format="%.3f")

    ports = [p.device for p in serial.tools.list_ports.comports()]
    selected_port = st.selectbox("Seleziona porta seriale:", ports if ports else ["Nessuna porta trovata"])
    baudrate = st.selectbox("Seleziona Baud Rate:", [9600, 19200, 38400, 57600, 115200], index=2)
    timeout = st.number_input("Timeout (secondi):", min_value=1, max_value=10, value=2)

    if st.button("Connetti / Reset"):
        st.session_state.stazione = SokkiaIXController(port=selected_port, baudrate=baudrate, timeout=timeout)

    st.markdown("---")

    if "stazione" in st.session_state and st.session_state.stazione.ser:
        st.subheader("Comandi Base")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📏 ESEGUI MISURA COMPLETA"):
                raw = st.session_state.stazione._send_command("D")
                if raw:
                    risultati = st.session_state.stazione.process_data(raw, h_i, h_p)
                    st.success("Misura acquisita!")
                    st.json(risultati)

        with col2:
            if st.button("📐 Leggi Tilt (Bolla)"):
                res = st.session_state.stazione._send_command("GT")
                st.info(f"Dati Inclinazione: {res}")

        with col3:
            if st.button("🔄 Azzeramento Cerchio H"):
                st.session_state.stazione._send_command("H0")
                st.warning("Cerchio Orizzontale Azzerato.")

        st.markdown("### Comandi Avanzati")
        col4, col5, col6 = st.columns(3)

        with col4:
            face = st.radio("Cambio Faccia (Motorizzato):", (1, 2), horizontal=True)
            if st.button("🔁 Ruota Cannocchiale"):
                with st.spinner("Rotazione in corso..."):
                    res = st.session_state.stazione.change_face(position=face)
                    st.info(f"Stato: {res}")

        with col5:
            laser_state = st.radio("Puntatore Laser:", ("Acceso", "Spento"), horizontal=True)
            if st.button("💡 Applica Laser"):
                state_bool = True if laser_state == "Acceso" else False
                st.session_state.stazione.laser_pointer(state=state_bool)
                st.info(f"Laser {'ON' if state_bool else 'OFF'}")

        with col6:
            if st.button("⏹ SPEGNI STRUMENTO"):
                st.session_state.stazione.power_off()
                st.error("Comando di spegnimento inviato.")

        # --- Monitoraggio automatico ---
        st.markdown("### Stato Strumento")
        st.write(f"Faccia attuale: {st.session_state.stazione.face}")
        st.write(f"Laser acceso: {st.session_state.stazione.laser_on}")
        if st.session_state.stazione.last_measure:
            st.write("Ultima misura:")
            st.json(st.session_state.stazione.last_measure)

        if auto_refresh:
            st.experimental_rerun()

if __name__ == "__main__":
    run_tps_monitoring(auto_refresh=False)
