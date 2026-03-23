# TPS_mod.py
import streamlit as st
import serial
import serial.tools.list_ports
import time

class SokkiaIXController:
    """Controller per Sokkia iX-1200 via seriale"""
    def __init__(self, port, baudrate=38400, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connect()

    def connect(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
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
            time.sleep(0.1)
            response = self.ser.readline().decode('ascii').strip()
            return response
        except Exception as e:
            st.error(f"Errore comunicazione: {e}")
            return None

    def parse_measure(self, raw):
        """Parsing minimale della misura (puoi adattarlo al formato reale)"""
        if not raw: return "Nessun dato"
        return {"Grezzo": raw}

    # --- Comandi aggiuntivi ---
    def change_face(self, position=1):
        """Cambia faccia motorizzata (1 o 2)"""
        cmd = "P1" if position == 1 else "P2"
        return self._send_command(cmd)

    def laser_pointer(self, state=True):
        """Accende o spegne laser"""
        cmd = "L1" if state else "L0"
        return self._send_command(cmd)

    def power_off(self):
        """Spegne la stazione"""
        return self._send_command("PW0")


def run_tps_monitoring():
    st.title("TPS Monitoring - Sokkia iX-1200")
    st.markdown("Controllo e monitoraggio della stazione totale Sokkia iX-1200")

    # --- Selezione Porta e Baud Rate ---
    ports = [p.device for p in serial.tools.list_ports.comports()]
    selected_port = st.selectbox("Seleziona porta seriale:", ports if ports else ["Nessuna porta trovata"])
    baudrate = st.selectbox("Seleziona Baud Rate:", [9600, 19200, 38400, 57600, 115200], index=2)
    timeout = st.number_input("Timeout (secondi):", min_value=1, max_value=10, value=2, step=1)

    # --- Pulsante di connessione ---
    if st.button("Connetti / Reset"):
        st.session_state.stazione = SokkiaIXController(port=selected_port, baudrate=baudrate, timeout=timeout)

    # --- Controlli principali base ---
    if "stazione" in st.session_state and st.session_state.stazione.ser:
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📏 Misura"):
                res = st.session_state.stazione._send_command("D")
                st.info(f"Risposta: {res}")

        with col2:
            if st.button("📐 Leggi Tilt"):
                res = st.session_state.stazione._send_command("GT")
                st.info(f"Tilt: {res}")

        with col3:
            if st.button("🔄 Azzeramento H"):
                res = st.session_state.stazione._send_command("H0")
                st.info("Comando Azzeramento inviato")

        st.markdown("---")  # Separatore per comandi avanzati

        # --- Comandi avanzati TPS ---
        col4, col5, col6 = st.columns(3)

        with col4:
            face = st.radio("Cambio Faccia:", (1, 2), horizontal=True)
            if st.button("🔁 Cambia Faccia"):
                res = st.session_state.stazione.change_face(position=face)
                st.info(f"Risultato Cambio Faccia: {res}")

        with col5:
            laser_state = st.radio("Laser:", ("Acceso", "Spento"), horizontal=True)
            if st.button("💡 Laser On/Off"):
                state_bool = True if laser_state == "Acceso" else False
                res = st.session_state.stazione.laser_pointer(state=state_bool)
                st.info(f"Risultato Laser: {res}")

        with col6:
            if st.button("⏹ Spegni Stazione"):
                res = st.session_state.stazione.power_off()
                st.info(f"Risultato Spegnimento: {res}")
