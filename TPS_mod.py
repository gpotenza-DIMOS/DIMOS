import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

def calculate_lrc(command):
    """Calcola il Checksum LRC richiesto dal protocollo Sokkia Standard"""
    lrc = 0
    for char in command:
        lrc = lrc ^ ord(char)
    return f"{lrc:02X}"

class SokkiaStandardController:
    def __init__(self, port, baudrate=38400):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connect()

    def connect(self):
        try:
            # Pulizia preventiva della porta
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=2
            )
            # Invia ACK iniziale per svegliare lo strumento
            self.ser.write(b"\x06") 
            st.success(f"✅ Connesso a {self.port} (Modalità Standard)")
        except Exception as e:
            st.error(f"Errore di connessione: {e}")

    def send_cmd(self, cmd_body):
        """Invia comando nel formato: [STX] 00 [CMD] [ETX] [LRC] [CRLF]"""
        payload = f"00{cmd_body}\x03" # ETX è \x03
        lrc = calculate_lrc(payload)
        full_msg = f"\x02{payload}{lrc}\r\n".encode('ascii') # STX è \x02
        
        try:
            self.ser.reset_input_buffer()
            self.ser.write(full_msg)
            time.sleep(0.5)
            
            # Legge la risposta
            response = self.ser.readline().decode('ascii', errors='ignore').strip()
            
            # Se lo strumento risponde con ACK (carattere 06), confermiamo
            if response.startswith('\x06'):
                self.ser.write(b"\x06") # Conferma ricezione
            
            return response
        except Exception as e:
            return f"Errore: {e}"

    def parse_data(self, raw, hi, hp):
        # Estrae i valori numerici dalla stringa complessa
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
            
            return {"Hz": hz, "V": v, "SD": sd, "dN": dN, "dE": dE, "dZ": dZ}
        except: return None

# --- INTERFACCIA ---
st.set_page_config(page_title="Sokkia iX Bridge", layout="wide")
st.title("🛰️ Sokkia iX-1200 - Protocollo Polifemo")

with st.sidebar:
    c_port = st.text_input("Porta COM", value="COM11")
    c_baud = st.selectbox("Baud Rate", [9600, 19200, 38400, 115200], index=2)
    h_i = st.number_input("Altezza Strumento (m)", value=1.500, format="%.3f")
    h_p = st.number_input("Altezza Prisma (m)", value=1.500, format="%.3f")
    if st.button("🔌 CONNETTI"):
        st.session_state.controller = SokkiaStandardController(c_port, c_baud)

if "controller" in st.session_state:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📏 ESEGUI MISURA"):
            # Comando 'M' (Measure) seguito da 'D' (Data)
            st.session_state.controller.send_cmd("M")
            time.sleep(1)
            raw = st.session_state.controller.send_cmd("D")
            res = st.session_state.controller.parse_data(raw, h_i, h_p)
            if res:
                st.write("### Risultati Calcolati")
                st.json(res)
            else:
                st.warning(f"Dati grezzi ricevuti: {raw}")

    with col2:
        if st.button("💡 LASER ON"):
            st.session_state.controller.send_cmd("L1")
        if st.button("🌑 LASER OFF"):
            st.session_state.controller.send_cmd("L0")
