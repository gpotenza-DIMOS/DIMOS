import streamlit as st
import serial
import time

class SokkiaDirect:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=2
            )
            return True
        except Exception as e:
            st.error(f"Errore connessione: {e}")
            return False

    def send_command(self, cmd):
        """Invia comando con terminazione CR-LF [cite: 11, 20]"""
        if self.ser and self.ser.is_open:
            full_command = f"{cmd}\r\n".encode('ascii') 
            self.ser.write(full_command)
            time.sleep(0.5)
            return self.ser.readline().decode('ascii', errors='ignore').strip()
        return "Errore: Porta chiusa"

def run_tps_monitoring():
    """Questa è la funzione che cerca il tuo file principale"""
    st.subheader("🛰️ Controllo Sokkia iX")

    col1, col2 = st.columns(2)
    with col1:
        port = st.text_input("Porta COM", value="COM11")
    with col2:
        baud = st.selectbox("Baud Rate", [4800, 9600, 19200], index=1)

    if st.button("🔌 Connetti"):
        st.session_state.tps = SokkiaDirect(port, baud)
        if st.session_state.tps.connect():
            st.success("Strumento connesso!")

    if "tps" in st.session_state:
        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("📏 Misura Distanza (11H)"):
                # Comando 11H per distanza e angoli [cite: 13]
                res = st.session_state.tps.send_command("11H")
                st.info(f"Dati: {res}")
        
        with c2:
            if st.button("🔄 Azzera Angolo (Xh)"):
                # Comando Xh per azzerare H [cite: 163]
                st.session_state.tps.send_command("Xh")
                st.toast("Angolo azzerato!")
