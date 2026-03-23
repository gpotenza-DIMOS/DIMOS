import streamlit as st
import serial
import serial.tools.list_ports
import time
import math
import re

class SokkiaIXController:
    def __init__(self, port, baudrate=9600, parity=serial.PARITY_NONE, stopbits=1, bytesize=8, flow_control="None", timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout
        self.xonxoff = True if flow_control == "Xon/Xoff" else False
        self.rtscts = True if flow_control == "RTS/CTS" else False
        self.ser = None
        self.connect()

    def connect(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            # Connessione diretta senza filtri (risolve il problema COM11 non trovata)
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
            
            # Sequenza di inizializzazione standard Sokkia (ACK)
            self.ser.write(b"\x06\r\n") 
            time.sleep(0.1)
            st.success(f"✅ Tentativo di connessione su {self.port} inviato.")
        except Exception as e:
            st.error(f"❌ Errore Hardware: {e}")
            self.ser = None

    def _send_command(self, command):
        if not self.ser or not self.ser.is_open:
            return "NON CONNESSO"
        try:
            self.ser.reset_input_buffer()
            # Protocollo robusto: STX (0x02) + Comando + ETX (0x03)
            # Molte iX richiedono i "00" davanti
            full_command = f"\x0200{command}\x03\r\n".encode("ascii")
            self.ser.write(full_command)
            
            time.sleep(0.5) # Aumentato per dare tempo ai motori della iX
            response = self.ser.readline().decode("ascii", errors="ignore").strip()
            
            # Pulizia dai caratteri di controllo della risposta
            clean_res = re.sub(r'[^\x20-\x7E]', '', response)
            return clean_res
        except Exception as e:
            return f"ERRORE: {e}"

    def measure_sequence(self, hi, hp):
        """Algoritmo di misura forzata"""
        # 1. Forza lo strumento a prendere una misura (distanza + angoli)
        st.write("🛰️ Calibrazione distanza in corso...")
        self._send_command("M") # Comando Measure
        time.sleep(1.5) 
        
        # 2. Richiede i dati dell'ultima misura effettuata
        raw = self._send_command("D")
        return self.process_data(raw, hi, hp)

    def process_data(self, raw, h_instr, h_reflector):
        if not raw or len(raw) < 5:
            return {"Errore": "Strumento non ha risposto o misura fallita", "Raw": raw}
        
        # L'algoritmo di parsing deve ignorare i prefissi '00' o 'D'
        matches = re.findall(r'[+-]\d+', raw)
        if len(matches) < 3:
            return {"Errore": "Dati incompleti (forse manca il prisma?)", "Raw": raw}
            
        try:
            hz_deg = float(matches[0]) / 100000
            v_deg = float(matches[1]) / 100000
            sd = float(matches[2]) / 1000

            hz_rad, v_rad = math.radians(hz_deg), math.radians(v_deg)
            hd = sd * math.sin(v_rad)
            dN = hd * math.cos(hz_rad)
            dE = hd * math.sin(hz_rad)
            dZ = (sd * math.cos(v_rad)) + h_instr - h_reflector

            return {
                "Stato": "OK",
                "Hz": f"{hz_deg:.4f}°",
                "V": f"{v_deg:.4f}°",
                "Distanza": f"{sd:.3f} m",
                "X (Est)": f"{dE:.3f} m",
                "Y (Nord)": f"{dN:.3f} m",
                "Z (Quota)": f"{dZ:.3f} m"
            }
        except Exception as e:
            return {"Errore": str(e), "Raw": raw}

# --- INTERFACCIA ---
def run_tps_monitoring():
    st.set_page_config(page_title="Sokkia iX-1200 Pro", layout="wide")
    
    # Parametri in Sidebar
    port_input = st.sidebar.text_input("Forza Porta COM", value="COM11")
    baud = st.sidebar.selectbox("Baud Rate", [4800, 9600, 19200, 38400], index=1)
    flow = st.sidebar.selectbox("Flow Control", ["None", "Xon/Xoff", "RTS/CTS"])
    hi = st.sidebar.number_input("H. Strumento", value=1.500)
    hp = st.sidebar.number_input("H. Prisma", value=1.500)

    if st.sidebar.button("🔌 APPLICA E CONNETTI"):
        st.session_state.stazione = SokkiaIXController(port=port_input, baudrate=baud, flow_control=flow)

    st.title("🛰️ Controllo Sokkia iX-1200")

    if "stazione" in st.session_state and st.session_state.stazione.ser:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📏 ESEGUI MISURA (M+D)"):
                with st.spinner("Puntando il prisma..."):
                    res = st.session_state.stazione.measure_sequence(hi, hp)
                    if res.get("Stato") == "OK":
                        st.success("Misura Effettuata")
                        st.table([res])
                    else:
                        st.error(res.get("Errore"))
                        st.write(f"Grezzo: {res.get('Raw')}")
        
        with c2:
            if st.button("📐 Check Tilt"):
                st.info(f"Dati: {st.session_state.stazione._send_command('GT')}")
        
        with c3:
            if st.button("💡 Laser ON/OFF"):
                # Toggle logico semplice
                current_laser = getattr(st.session_state, 'laser_state', False)
                cmd = "L1" if not current_laser else "L0"
                st.session_state.stazione._send_command(cmd)
                st.session_state.laser_state = not current_laser
                st.write(f"Laser: {'ACCESO' if not current_laser else 'SPENTO'}")

if __name__ == "__main__":
    run_tps_monitoring()
