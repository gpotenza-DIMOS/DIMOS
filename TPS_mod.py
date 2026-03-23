import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

def calculate_checksum(command):
    """Calcola il Checksum (LRC) per protocollo Sokkia Standard"""
    checksum = 0
    for char in command:
        checksum = checksum ^ ord(char)
    return f"{checksum:02X}"

class SokkiaStandardController:
    def __init__(self, port, baudrate=38400, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connect()

    def connect(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=self.timeout
            )
            # Inizializzazione con ACK (06) come vuole Polifemo
            self.ser.write(b"\x06") 
            st.success(f"✅ Protocollo Sokkia Standard inizializzato su {self.port}")
        except Exception as e:
            st.error(f"❌ Errore apertura porta: {e}")

    def send_standard_command(self, cmd_body):
        """Invia comando con STX, ETX e Checksum"""
        # Formato: STX + Corpo + ETX + Checksum + CR + LF
        full_payload = f"00{cmd_body}\x03" # 00 + comando + ETX
        csum = calculate_checksum(full_payload)
        final_msg = f"\x02{full_payload}{csum}\r\n".encode('ascii')
        
        try:
            self.ser.reset_input_buffer()
            self.ser.write(final_msg)
            time.sleep(0.6)
            response = self.ser.readline().decode('ascii', errors='ignore').strip()
            return response
        except Exception as e:
            return f"Errore: {e}"

    def process_data(self, raw, hi, hp):
        # Estrazione numeri (angoli e distanze)
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

# --- UI STREAMLIT ---
st.title("🛰️ Python Bridge for Sokkia iX (Standard Mode)")

with st.sidebar:
    port = st.text_input("Porta COM", value="COM11")
    baud = st.selectbox("Baud Rate", [9600, 19200, 38400, 115200], index=2)
    hi = st.number_input("Altezza Strumento", value=1.500)
    hp = st.number_input("Altezza Prisma", value=1.500)
    if st.button("🔌 Connetti"):
        st.session_state.ix = SokkiaStandardController(port, baud)

if "ix" in st.session_state:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📏 ESEGUI MISURA"):
            # 'M' avvia la misura, 'D' legge i dati
            st.session_state.ix.send_standard_command("M")
            time.sleep(1.5)
            raw = st.session_state.ix.send_standard_command("D")
            res = st.session_state.ix.process_data(raw, hi, hp)
            if res: st.write(res)
            else: st.warning(f"Risposta grezza: {raw}")
    
    with col2:
        if st.button("💡 LASER ON"):
            st.session_state.ix.send_standard_command("L1")
        if st.button("🌑 LASER OFF"):
            st.session_state.ix.send_standard_command("L0")
