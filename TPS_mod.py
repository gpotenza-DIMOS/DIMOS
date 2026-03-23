import streamlit as st
import serial
import time
import math
import re

def calculate_sokkia_lrc(payload):
    """
    Calcola l'LRC (Longitudinal Redundancy Check) come descritto nel manuale.
    Si esegue lo XOR di tutti i caratteri tra STX (escluso) ed ETX (incluso).
    """
    lrc = 0
    for char in payload:
        lrc ^= ord(char)
    return f"{lrc:02X}"

class SokkiaProtocol:
    def __init__(self, port, baudrate=38400):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.stx = "\x02"
        self.etx = "\x03"
        self.ack = "\x06"

    def connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=3
            )
            # Inizializzazione: invia un ACK per pulire il buffer dello strumento
            self.ser.write(self.ack.encode())
            return True
        except Exception as e:
            st.error(f"Errore connessione: {e}")
            return False

    def send_command(self, cmd):
        """Impacchetta il comando secondo il manuale: [STX]corpo[ETX][LRC][CR][LF]"""
        body = f"00{cmd}{self.etx}" 
        lrc = calculate_sokkia_lrc(body)
        full_msg = f"{self.stx}{body}{lrc}\r\n"
        
        try:
            self.ser.reset_input_buffer()
            self.ser.write(full_msg.encode('ascii'))
            
            # Attesa risposta
            time.sleep(0.5)
            response = self.ser.readline().decode('ascii', errors='ignore')
            
            # Se lo strumento risponde correttamente, mandiamo un ACK di conferma
            if response:
                self.ser.write(self.ack.encode())
                
            return response
        except Exception as e:
            return f"Errore invio: {e}"

# --- INTERFACCIA STREAMLIT ---
st.title("🛰️ Sokkia iX - Manual Protocol Bridge")

# Campi di input
col_conf1, col_conf2 = st.columns(2)
with col_conf1:
    port = st.text_input("Porta COM", value="COM11")
with col_conf2:
    baud = st.selectbox("Baud Rate", [4800, 9600, 19200, 38400], index=3)

if st.button("🔌 Inizializza Strumento"):
    st.session_state.tps = SokkiaProtocol(port, baud)
    if st.session_state.tps.connect():
        st.success("Strumento Pronto (Protocollo SDR20)")

if "tps" in st.session_state:
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if st.button("📏 MISURA (Distanza+Angoli)"):
            # Il manuale suggerisce 'M' per trigger e 'D' per scarico dati
            st.write("Invio comando misura...")
            st.session_state.tps.send_command("M")
            time.sleep(2) # Tempo per l'EDM
            raw_data = st.session_state.tps.send_command("D")
            st.code(raw_data, language="text")
            
    with c2:
        if st.button("💡 LASER ON"):
            st.session_state.tps.send_command("L1")
        if st.button("🌑 LASER OFF"):
            st.session_state.tps.send_command("L0")

    with c3:
        if st.button("🔄 AZZERA H (H0)"):
            st.session_state.tps.send_command("H0")
