# TPS_mod.py
import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

class SokkiaIXController:
    """Controller per Sokkia iX-1200 con parametri avanzati"""
    def __init__(self, port, baudrate=9600, parity=serial.PARITY_NONE, stopbits=1, bytesize=8, flow_control="None", timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout

        # Flow control
        self.xonxoff = True if flow_control == "Xon/Xoff" else False
        self.rtscts = True if flow_control == "RTS/CTS" else False

        self.ser = None
        self.laser_on = False
        self.face = 1
        self.connect()

    def connect(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout,
                xonxoff=self.xonxoff,
                rtscts=self.rtscts
            )
            # Wakeup protocollo Sokkia
            self.ser.write(b"\x06\r\n")
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
            self.ser.write(f"00{command}\r\n".encode("ascii"))
            time.sleep(0.2)
            response = self.ser.readline().decode("ascii").strip()
            return response
        except Exception as e:
            st.error(f"Errore comunicazione: {e}")
            return None

    def process_data(self, raw, h_instr=1.50, h_reflector=1.50):
        """Parsing base dati Sokkia iX"""
        if not raw or len(raw) < 5:
            return None
        try:
            matches = re.findall(r'[+-]?\d+', raw)
            if len(matches) < 3:
                return {"Errore": "Formato stringa non riconosciuto", "Raw": raw}
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

    # Comandi avanzati
    def change_face(self, position=1):
        cmd = "P1" if position == 1 else "P2"
        return self._send_command(cmd)

    def laser_pointer(self, state=True):
        cmd = "L1" if state else "L0"
        return self._send_command(cmd)

    def power_off(self):
        return self._send_command("PW0")

# Funzione Streamlit fuori dalla classe
def run_tps_monitoring():
    st.set_page_config(page_title="Sokkia iX-1200 Controller", layout="wide")
    st.title("🛰️ TPS Monitoring - Sokkia iX-1200")

    # Sidebar parametri altezze
    st.sidebar.header("Parametri di Calcolo")
    h_instr = st.sidebar.number_input("Altezza Strumento (m)", value=1.500, format="%.3f")
    h_ref = st.sidebar.number_input("Altezza Prisma (m)", value=1.500, format="%.3f")

    # Configurazione seriale
    st.sidebar.header("Parametri Comunicazione")
    ports = [p.device for p in serial.tools.list_ports.comports()]
    selected_port = st.text_input("Porta COM", value="COM11")
    baudrate = st.selectbox("Baud Rate", [1200,2400,4800,9600,19200,38400,115200], index=3)
    data_bits = st.selectbox("Data Bits", [7,8], index=1)
    parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
    parity_sel = st.selectbox("Parity", list(parity_map.keys()))
    stop_bits = st.selectbox("Stop Bits", [1,1.5,2], index=0)
    flow_ctrl = st.selectbox("Flow Control", ["None","Xon/Xoff","RTS/CTS"])

    if st.button("🔌 Connetti / Reset"):
        st.session_state.stazione = SokkiaIXController(
            port=selected_port,
            baudrate=baudrate,
            bytesize=data_bits,
            parity=parity_map[parity_sel],
            stopbits=stop_bits,
            flow_control=flow_ctrl
        )

    # Controlli principali
    if "stazione" in st.session_state and st.session_state.stazione.ser:
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📏 ESEGUI MISURA"):
                raw = st.session_state.stazione._send_command("D")
                if raw:
                    res = st.session_state.stazione.process_data(raw,h_instr,h_ref)
                    st.json(res)

        with col2:
            if st.button("📐 Leggi Tilt"):
                tilt = st.session_state.stazione._send_command("GT")
                st.info(f"Tilt: {tilt}")

        with col3:
            if st.button("🔄 Azzeramento H"):
                st.session_state.stazione._send_command("H0")
                st.warning("Cerchio orizzontale azzerato.")

        st.markdown("### Comandi avanzati")
        col4, col5, col6 = st.columns(3)

        with col4:
            face = st.radio("Cambio Faccia", (1,2), horizontal=True)
            if st.button("🔁 Ruota Cannocchiale"):
                res = st.session_state.stazione.change_face(face)
                st.info(f"Stato cambio faccia: {res}")

        with col5:
            laser_state = st.radio("Laser", ("Acceso","Spento"), horizontal=True)
            if st.button("💡 Applica Laser"):
                state_bool = True if laser_state=="Acceso" else False
                st.session_state.stazione.laser_pointer(state_bool)

        with col6:
            if st.button("⏹ Spegni Strumento"):
                st.session_state.stazione.power_off()
                st.error("Comando di spegnimento inviato.")
