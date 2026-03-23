import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

# =========================
# CONTROLLER SOKKIA
# =========================
class SokkiaIXController:
    def __init__(self, port, baudrate, parity, stopbits, bytesize, flow_control, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout

        self.xonxoff = flow_control == "Xon/Xoff"
        self.rtscts = flow_control == "RTS/CTS"

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
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
                xonxoff=self.xonxoff,
                rtscts=self.rtscts
            )

            self.ser.write(b"\r\n")
            st.success(f"✅ Connesso a {self.port}")

        except Exception as e:
            st.error(f"❌ Errore connessione: {e}")
            self.ser = None

    def _send_command(self, command):
        if not self.ser or not self.ser.is_open:
            st.warning("Strumento non connesso")
            return None
        try:
            self.ser.reset_input_buffer()
            self.ser.write(f"00{command}\r\n".encode("ascii"))
            time.sleep(0.3)
            return self.ser.readline().decode("ascii").strip()
        except Exception as e:
            st.error(f"Errore comunicazione: {e}")
            return None

    # =========================
    # CALCOLO TOPOGRAFICO
    # =========================
    def process_data(self, raw, h_instr=1.5, h_prism=1.5):
        if not raw:
            return None

        matches = re.findall(r'[+-]?\d+', raw)
        if len(matches) < 3:
            return {"Errore": "Formato non riconosciuto", "Raw": raw}

        try:
            hz = float(matches[0]) / 100000
            v = float(matches[1]) / 100000
            sd = float(matches[2]) / 1000

            hz_rad = math.radians(hz)
            v_rad = math.radians(v)

            hd = sd * math.sin(v_rad)
            dN = hd * math.cos(hz_rad)
            dE = hd * math.sin(hz_rad)
            dZ = (sd * math.cos(v_rad)) + h_instr - h_prism

            self.last_measure = {
                "Hz": hz,
                "V": v,
                "SD": sd,
                "HD": hd,
                "dN": dN,
                "dE": dE,
                "dZ": dZ
            }

            return self.last_measure

        except Exception as e:
            return {"Errore": str(e), "Raw": raw}

    # =========================
    # COMANDI TPS
    # =========================
    def change_face(self, pos):
        self.face = pos
        return self._send_command("P1" if pos == 1 else "P2")

    def laser(self, state):
        self.laser_on = state
        return self._send_command("L1" if state else "L0")

    def power_off(self):
        return self._send_command("PW0")


# =========================
# INTERFACCIA STREAMLIT
# =========================
def run_tps_monitoring():

    st.title("🛰️ TPS Monitoring - Sokkia iX")

    # =========================
    # PARAMETRI COMUNICAZIONE
    # =========================
    with st.expander("⚙️ Parametri Seriali", expanded=True):

        col1, col2, col3 = st.columns(3)

        with col1:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            forced_port = st.text_input("Forza Porta (es. COM11)")
            port = forced_port if forced_port else (ports[0] if ports else "")

            baud = st.selectbox("Baudrate", [9600,19200,38400,57600,115200], index=2)

        with col2:
            data_bits = st.selectbox("Data Bits", [7,8], index=1)
            bytesize = {7: serial.SEVENBITS, 8: serial.EIGHTBITS}[data_bits]

            parity_map = {
                "None": serial.PARITY_NONE,
                "Even": serial.PARITY_EVEN,
                "Odd": serial.PARITY_ODD
            }
            parity_sel = st.selectbox("Parity", list(parity_map.keys()))

        with col3:
            stop_map = {
                1: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2: serial.STOPBITS_TWO
            }
            stop_sel = st.selectbox("Stop Bits", [1,1.5,2])

            flow = st.selectbox("Flow Control", ["None","Xon/Xoff","RTS/CTS"])

        if st.button("🔌 Connetti"):
            st.session_state.stazione = SokkiaIXController(
                port=port,
                baudrate=baud,
                parity=parity_map[parity_sel],
                stopbits=stop_map[stop_sel],
                bytesize=bytesize,
                flow_control=flow
            )

    # =========================
    # PARAMETRI TOPOGRAFICI
    # =========================
    st.sidebar.header("Parametri Topografici")
    h_i = st.sidebar.number_input("Altezza Strumento", value=1.5)
    h_p = st.sidebar.number_input("Altezza Prisma", value=1.5)

    # =========================
    # CONTROLLO STRUMENTO
    # =========================
    if "stazione" in st.session_state and st.session_state.stazione.ser:

        st.markdown("## 🎯 Comandi")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📏 Misura"):
                raw = st.session_state.stazione._send_command("D")
                res = st.session_state.stazione.process_data(raw, h_i, h_p)
                st.json(res)

        with col2:
            if st.button("📐 Tilt"):
                res = st.session_state.stazione._send_command("GT")
                st.write(res)

        with col3:
            if st.button("🔄 Azzera H"):
                st.session_state.stazione._send_command("H0")

        st.markdown("## ⚙️ Avanzati")

        col4, col5, col6 = st.columns(3)

        with col4:
            face = st.radio("Faccia", [1,2])
            if st.button("🔁 Ruota"):
                st.session_state.stazione.change_face(face)

        with col5:
            laser = st.radio("Laser", ["ON","OFF"])
            if st.button("💡 Applica"):
                st.session_state.stazione.laser(laser=="ON")

        with col6:
            if st.button("⏹ Spegni"):
                st.session_state.stazione.power_off()

        # =========================
        # STATO
        # =========================
        st.markdown("## 📊 Stato")

        st.write("Faccia:", st.session_state.stazione.face)
        st.write("Laser:", st.session_state.stazione.laser_on)

        if st.session_state.stazione.last_measure:
            st.json(st.session_state.stazione.last_measure)


if __name__ == "__main__":
    run_tps_monitoring()
