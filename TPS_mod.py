import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

class SokkiaIXController:
    def __init__(self, port, baudrate, parity, stopbits, bytesize, flow_control, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout
        
        # Gestione Flow Control (fondamentale per Sokkia iX)
        self.xonxoff = True if flow_control == "Xon/Xoff" else False
        self.rtscts = True if flow_control == "RTS/CTS" else False
        
        self.ser = None
        self.last_measure = None
        self.connect()

    def connect(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            # Apertura porta con tutti i parametri del tuo printscreen
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
            # Wake up e check iniziale
            self.ser.write(b"\x06\r\n") 
            st.success(f"✅ Connesso a {self.port} (Baud: {self.baudrate})")
        except Exception as e:
            st.error(f"❌ Impossibile aprire {self.port}. Verifica che non sia usata da altri programmi. Errore: {e}")
            self.ser = None

    def _send_command(self, command):
        if not self.ser or not self.ser.is_open: return None
        try:
            self.ser.reset_input_buffer()
            # Prefisso '00' obbligatorio per protocollo Sokkia
            self.ser.write(f"00{command}\r\n".encode('ascii'))
            time.sleep(0.3) 
            return self.ser.readline().decode('ascii').strip()
        except Exception as e:
            st.error(f"Errore: {e}")
            return None

    def calculate_coords(self, raw, hi, hp):
        """Algoritmo: trasforma dati grezzi in coordinate Nord, Est, Quota"""
        matches = re.findall(r'[+-]\d+', raw)
        if len(matches) < 3: return None
        try:
            hz = float(matches[0]) / 100000
            v = float(matches[1]) / 100000
            sd = float(matches[2]) / 1000
            
            hz_rad, v_rad = math.radians(hz), math.radians(v)
            hd = sd * math.sin(v_rad)
            dN = hd * math.cos(hz_rad)
            dE = hd * math.sin(hz_rad)
            dZ = (sd * math.cos(v_rad)) + hi - hp
            
            self.last_measure = {"Hz": hz, "V": v, "SD": sd, "dN": dN, "dE": dE, "dZ": dZ}
            return self.last_measure
        except: return None

# --- INTERFACCIA STREAMLIT ---
def run_tps_monitoring():
    st.set_page_config(page_title="Sokkia iX-1200 Control", layout="wide")
    st.title("🛰️ Controllo Totale Sokkia iX-1200")

    # Sidebar: Configurazione Porta (come nel tuo printscreen)
    st.sidebar.header("Impostazioni Seriale")
    port_input = st.sidebar.text_input("Porta COM:", value="COM11")
    baud = st.sidebar.selectbox("Baud Rate:", [4800, 9600, 19200, 38400, 115200], index=3)
    dbits = st.sidebar.selectbox("Data Bits:", [7, 8], index=1)
    pari = st.sidebar.selectbox("Parity:", ["None", "Even", "Odd"])
    stopb = st.sidebar.selectbox("Stop Bits:", [1, 2], index=0)
    flow = st.sidebar.selectbox("Flow Control:", ["None", "Xon/Xoff", "RTS/CTS"])
    
    st.sidebar.markdown("---")
    hi = st.sidebar.number_input("Altezza Strumento (m):", value=1.500, format="%.3f")
    hp = st.sidebar.number_input("Altezza Prisma (m):", value=1.500, format="%.3f")

    if st.sidebar.button("🔌 CONNETTI"):
        p_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
        st.session_state.stazione = SokkiaIXController(port_input, baud, p_map[pari], stopb, dbits, flow)

    # Area Comandi
    if "stazione" in st.session_state and st.session_state.stazione.ser:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📏 MISURA"):
                raw = st.session_state.stazione._send_command("D")
                res = st.session_state.stazione.calculate_coords(raw, hi, hp)
                if res:
                    st.metric("Dist. Orizzontale", f"{res['SD']*math.sin(math.radians(res['V'])):.3f} m")
                    st.json(res)
        with col2:
            if st.button("📐 TILT"):
                st.info(f"Tilt: {st.session_state.stazione._send_command('GT')}")
        with col3:
            if st.button("🔄 AZZERA H"):
                st.session_state.stazione._send_command("H0")
                st.warning("Cerchio H Azzerato")

        # Comandi Avanzati
        st.markdown("---")
        c4, c5 = st.columns(2)
        with c4:
            f = st.radio("Faccia:", (1, 2), horizontal=True)
            if st.button("🔁 CAMBIA FACCIA"):
                st.session_state.stazione._send_command(f"P{f}")
        with c5:
            if st.button("💡 LASER ON"): st.session_state.stazione._send_command("L1")
            if st.button("🌑 LASER OFF"): st.session_state.stazione._send_command("L0")

if __name__ == "__main__":
    run_tps_monitoring()
