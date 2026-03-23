import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

class SokkiaIXController:
    """Controller per Sokkia iX-1200 con logica di parsing avanzata"""
    def __init__(self, port, baudrate, parity, stopbits, bytesize, flow_control, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout
        
        # Gestione Flow Control
        self.xonxoff = True if flow_control == "Xon/Xoff" else False
        self.rtscts = True if flow_control == "RTS/CTS" else False
        
        self.ser = None
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
            # Inizializzazione protocollo
            self.ser.write(b"\x06\r\n") 
            st.success(f"✅ Connesso a {self.port}")
        except Exception as e:
            st.error(f"❌ Errore Hardware sulla porta {self.port}: {e}")
            self.ser = None

    def _send_command(self, command):
        if not self.ser or not self.ser.is_open:
            return None
        try:
            self.ser.reset_input_buffer()
            # Protocollo Sokkia: 00 + Comando + CR/LF
            msg = f"00{command}\r\n".encode('ascii')
            self.ser.write(msg)
            time.sleep(0.4) # Tempo per la meccanica iX
            response = self.ser.readline().decode('ascii', errors='ignore').strip()
            return response
        except Exception as e:
            return f"Errore: {e}"

    def calculate_coordinates(self, raw, hi, hp):
        """Algoritmo per trasformare i dati grezzi in coordinate"""
        if not raw: return None
        # Estrae i blocchi numerici (+00123...)
        matches = re.findall(r'[+-]\d+', raw)
        if len(matches) < 3: return {"Errore": "Dati incompleti", "Raw": raw}
        
        try:
            hz = float(matches[0]) / 100000
            v = float(matches[1]) / 100000
            sd = float(matches[2]) / 1000
            
            hz_rad = math.radians(hz)
            v_rad = math.radians(v)
            
            hd = sd * math.sin(v_rad)
            dN = hd * math.cos(hz_rad)
            dE = hd * math.sin(hz_rad)
            dZ = (sd * math.cos(v_rad)) + hi - hp
            
            return {
                "Hz": f"{hz:.4f}°",
                "V": f"{v:.4f}°",
                "SD": f"{sd:.3f} m",
                "HD": f"{hd:.3f} m",
                "N (Y)": f"{dN:.3f} m",
                "E (X)": f"{dE:.3f} m",
                "Z (Quota)": f"{dZ:.3f} m"
            }
        except:
            return {"Errore": "Calcolo fallito", "Raw": raw}

def run_tps_monitoring():
    st.title("🛰️ Sokkia iX-1200 Control Center")

    # --- Configurazione Seriale ---
    st.sidebar.header("🔌 Impostazioni Seriale")
    
    # Risoluzione automatica porte per evitare errori di battitura
    ports_detected = [p.device for p in serial.tools.list_ports.comports()]
    default_port = "COM11" if "COM11" in ports_detected else (ports_detected[0] if ports_detected else "COM1")
    
    sel_port = st.sidebar.text_input("Porta COM:", value=default_port)
    baud = st.sidebar.selectbox("Baud Rate:", [4800, 9600, 19200, 38400, 115200], index=3)
    
    # Mappatura Parità (Risolve il NameError dello screenshot)
    p_options = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
    p_key = st.sidebar.selectbox("Parity:", list(p_options.keys()))
    
    flow = st.sidebar.selectbox("Flow Control:", ["None", "Xon/Xoff", "RTS/CTS"])
    
    st.sidebar.markdown("---")
    st.sidebar.header("📏 Geometria")
    hi = st.sidebar.number_input("Altezza Strumento", value=1.500, format="%.3f")
    hp = st.sidebar.number_input("Altezza Prisma", value=1.500, format="%.3f")

    if st.sidebar.button("CONNETTI STRUMENTO"):
        st.session_state.stazione = SokkiaIXController(
            port=sel_port, 
            baudrate=baud, 
            parity=p_options[p_key], 
            stopbits=1, 
            bytesize=8, 
            flow_control=flow
        )

    # --- Area Operativa ---
    if "stazione" in st.session_state and st.session_state.stazione.ser:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📏 MISURA"):
                # Sequenza: Forza misura (M) e poi leggi (D)
                st.session_state.stazione._send_command("M")
                time.sleep(1)
                raw = st.session_state.stazione._send_command("D")
                if raw:
                    data = st.session_state.stazione.calculate_coordinates(raw, hi, hp)
                    st.json(data)
                else:
                    st.error("Lo strumento non risponde.")

        with col2:
            if st.button("📐 LEGGI TILT"):
                res = st.session_state.stazione._send_command("GT")
                st.info(f"Tilt: {res}")

        with col3:
            if st.button("💡 LASER ON/OFF"):
                # Semplice toggle laser
                st.session_state.stazione._send_command("L1")
                st.success("Comando Laser inviato")

if __name__ == "__main__":
    run_tps_monitoring()
