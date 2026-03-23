# TPS_mod.py
import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

class SokkiaIXController:
    """Controller Sokkia iX-1200 compatibile Windows, con gestione porta COM flessibile"""
    
    def __init__(self, port="COM11", baudrate=9600, parity=serial.PARITY_NONE,
                 stopbits=1, bytesize=8, flow_control="None", timeout=2, prefisso="00"):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout
        self.prefisso = prefisso
        
        # Flow control
        self.xonxoff = True if flow_control == "Xon/Xoff" else False
        self.rtscts = True if flow_control == "RTS/CTS" else False
        
        self.ser = None
        self.face = 1
        self.laser_on = False
        self.last_measure = None
        self.connect()
    
    def connect(self):
        # Verifica che la porta COM esista
        available_ports = [p.device for p in serial.tools.list_ports.comports()]
        if self.port not in available_ports:
            st.error(f"❌ Porta {self.port} non trovata. Porte disponibili: {available_ports}")
            self.ser = None
            return
        
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
                xonxoff=self.xonxoff,
                rtscts=self.rtscts
            )
            # Wake up call
            self.ser.write(f"{self.prefisso}\r\n".encode("ascii"))
            st.success(f"✅ Connesso a {self.port} @ {self.baudrate} baud")
        except Exception as e:
            st.error(f"❌ Errore connessione: {e}")
            self.ser = None

    def _send_command(self, command, delay=0.5):
        """Invio comando alla stazione totale con timeout e lettura risposta"""
        if not self.ser or not self.ser.is_open:
            st.warning("Strumento non connesso.")
            return None
        try:
            self.ser.reset_input_buffer()
            full_cmd = f"{self.prefisso}{command}\r\n"
            self.ser.write(full_cmd.encode("ascii"))
            time.sleep(delay)
            response = self.ser.readline().decode("ascii", errors="ignore").strip()
            return response
        except Exception as e:
            st.error(f"Errore comunicazione: {e}")
            return None

    def process_data(self, raw, h_instr=1.50, h_reflector=1.50):
        """Parsing base e calcolo coordinate relative"""
        if not raw or len(raw) < 5:
            return {"Errore": "Nessun dato ricevuto", "Raw": raw}
        matches = re.findall(r"[+-]?\d+", raw)
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
            return {
                "Angolo Hz": f"{hz_deg:.4f}°",
                "Angolo V": f"{v_deg:.4f}°",
                "Dist. Inclinata": f"{sd:.3f} m",
                "Dist. Orizzontale": f"{hd:.3f} m",
                "Delta Nord (Y)": f"{dN:.3f} m",
                "Delta Est (X)": f"{dE:.3f} m",
                "Delta Quota (Z)": f"{dZ:.3f} m"
            }
        except Exception as e:
            return {"Errore": str(e), "Raw": raw}

    # --- Comandi avanzati ---
    def change_face(self, position=1):
        cmd = "P1" if position == 1 else "P2"
        return self._send_command(cmd)
    
    def laser_pointer(self, state=True):
        cmd = "L1" if state else "L0"
        return self._send_command(cmd)
    
    def power_off(self):
        return self._send_command("PW0")


def run_tps_monitoring():
    """Interfaccia Streamlit per TPS"""
    st.set_page_config(page_title="Sokkia iX-1200 Controller", layout="wide")
    st.title("🛰️ TPS Monitoring - Sokkia iX-1200")

    # --- Parametri calcolo coordinate ---
    st.sidebar.header("Parametri di Calcolo")
    h_instr = st.sidebar.number_input("Altezza Strumento (m)", value=1.500, format="%.3f")
    h_ref = st.sidebar.number_input("Altezza Prisma (m)", value=1.500, format="%.3f")

    # --- Parametri seriale ---
    st.sidebar.header("Parametri Seriali")
    ports = [p.device for p in serial.tools.list_ports.comports()]
    selected_port = st.text_input("Porta COM:", value="COM11")
    baudrate = st.selectbox("Baud Rate:", [1200, 2400, 4800, 9600, 19200, 38400, 115200], index=4)
    parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
    parity_sel = st.selectbox("Parity:", list(parity_map.keys()), index=0)
    stop_bits = st.selectbox("Stop Bits:", [1, 1.5, 2], index=0)
    data_bits = st.selectbox("Data Bits:", [7, 8], index=1)
    flow_ctrl = st.selectbox("Flow Control:", ["None", "Xon/Xoff", "RTS/CTS"])

    if st.button("🔌 Connetti / Reset"):
        st.session_state.stazione = SokkiaIXController(
            port=selected_port,
            baudrate=baudrate,
            parity=parity_map[parity_sel],
            stopbits=stop_bits,
            bytesize=data_bits,
            flow_control=flow_ctrl
        )

    if "stazione" in st.session_state and st.session_state.stazione.ser:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📏 ESEGUI MISURA"):
                raw = st.session_state.stazione._send_command("D")
                res = st.session_state.stazione.process_data(raw, h_instr, h_ref)
                st.json(res)

        with col2:
            if st.button("📐 Leggi Tilt"):
                tilt = st.session_state.stazione._send_command("GT")
                st.info(f"Tilt: {tilt}")

        with col3:
            if st.button("🔄 Azzeramento H"):
                st.session_state.stazione._send_command("H0")
                st.warning("Cerchio H azzerato.")

        st.markdown("### Comandi Avanzati")
        col4, col5, col6 = st.columns(3)

        with col4:
            face = st.radio("Cambio Faccia:", (1,2), horizontal=True)
            if st.button("🔁 Ruota Cannocchiale"):
                with st.spinner("Rotazione..."):
                    res = st.session_state.stazione.change_face(position=face)
                    st.info(f"Stato: {res}")

        with col5:
            laser_state = st.radio("Puntatore Laser:", ("Acceso","Spento"), horizontal=True)
            if st.button("💡 Applica Laser"):
                state_bool = True if laser_state=="Acceso" else False
                res = st.session_state.stazione.laser_pointer(state=state_bool)
                st.info(f"Laser: {'Acceso' if state_bool else 'Spento'}")

        with col6:
            if st.button("⏹ Spegni Strumento"):
                st.session_state.stazione.power_off()
                st.error("Comando di spegnimento inviato.")
