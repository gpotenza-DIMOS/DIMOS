import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

# Definiamo le costanti per evitare il NameError nel corpo del codice
PARITY_MAP = {
    "None": serial.PARITY_NONE,
    "Even": serial.PARITY_EVEN,
    "Odd": serial.PARITY_ODD
}

class SokkiaIXController:
    def __init__(self, port, baudrate, parity, flow_control, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.timeout = timeout
        self.xonxoff = True if flow_control == "Xon/Xoff" else False
        self.rtscts = True if flow_control == "RTS/CTS" else False
        self.ser = None
        self.connect()

    def connect(self):
        try:
            # Chiude eventuali connessioni residue
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            # Apertura diretta della porta (ignora i filtri di sistema)
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=self.timeout,
                xonxoff=self.xonxoff,
                rtscts=self.rtscts
            )
            
            # Protocollo di "bussata" Sokkia
            self.ser.write(b"\x06\r\n") 
            st.success(f"✅ COMUNICAZIONE ATTIVA SU {self.port}")
        except Exception as e:
            st.error(f"❌ Errore critico sulla {self.port}: {e}")
            st.info("Suggerimento: Chiudi altri software che usano lo strumento (es. Topcon Link o terminali).")
            self.ser = None

    def _send_command(self, command):
        if not self.ser or not self.ser.is_open:
            return "NON CONNESSO"
        try:
            self.ser.reset_input_buffer()
            # Protocollo standard 00 + Comando + CR+LF
            full_cmd = f"00{command}\r\n".encode('ascii')
            self.ser.write(full_cmd)
            time.sleep(0.5) 
            response = self.ser.readline().decode('ascii', errors='ignore').strip()
            return response
        except Exception as e:
            return f"Errore: {e}"

    def process_measure(self, raw, hi, hp):
        if not raw: return None
        matches = re.findall(r'[+-]\d+', raw)
        if len(matches) < 3: return {"Errore": "Dati incompleti", "Raw": raw}
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

# --- INTERFACCIA STREAMLIT ---
def run_tps_monitoring():
    st.set_page_config(page_title="Sokkia iX-1200", layout="wide")
    st.title("🛰️ Sokkia iX-1200 - Controllo Avanzato")

    # Parametri Seriale
    with st.sidebar:
        st.header("⚙️ Configurazione")
        port_name = st.text_input("Porta (Scrivi COM11)", value="COM11")
        baud = st.selectbox("Baud Rate", [9600, 19200, 38400, 115200], index=2)
        parity_sel = st.selectbox("Parità", ["None", "Even", "Odd"])
        flow = st.selectbox("Flow Control", ["None", "Xon/Xoff", "RTS/CTS"])
        
        st.markdown("---")
        hi = st.number_input("H. Strumento", value=1.500, format="%.3f")
        hp = st.number_input("H. Prisma", value=1.500, format="%.3f")
        
        if st.button("🔌 CONNETTI"):
            st.session_state.stazione = SokkiaIXController(
                port=port_name,
                baudrate=baud,
                parity=PARITY_MAP[parity_sel],
                flow_control=flow
            )

    # Comandi
    if "stazione" in st.session_state and st.session_state.stazione.ser:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📏 MISURA ORA"):
                # Sequenza M (Measure) + D (Get Data)
                st.session_state.stazione._send_command("M")
                time.sleep(1.5)
                raw = st.session_state.stazione._send_command("D")
                res = st.session_state.stazione.process_measure(raw, hi, hp)
                if res:
                    st.write("### Risultati")
                    st.table([res])
        with c2:
            if st.button("📐 LEGGI TILT"):
                tilt = st.session_state.stazione._send_command("GT")
                st.info(f"Tilt: {tilt}")
        with c3:
            if st.button("💡 LASER ON/OFF"):
                st.session_state.stazione._send_command("L1")
                st.success("Comando inviato")

if __name__ == "__main__":
    run_tps_monitoring()
