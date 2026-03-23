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
            st.error(f"Errore di connessione: {e}")
            return False

    def send_command(self, cmd):
        """Invia il comando con terminazione CR-LF come richiesto dal manuale"""
        if self.ser and self.ser.is_open:
            full_command = f"{cmd}\r\n".encode('ascii') # 
            self.ser.write(full_command)
            time.sleep(0.5)
            # Legge la risposta fino al CR-LF
            response = self.ser.readline().decode('ascii', errors='ignore').strip()
            return response
        return "Errore: Porta seriale non aperta"

# --- INTERFACCIA STREAMLIT ---
st.title("🛰️ Sokkia iX - Direct Controller")

col1, col2 = st.columns(2)
with col1:
    port = st.text_input("Porta COM (es. COM11)", value="COM11")
with col2:
    baud = st.selectbox("Baud Rate", [1200, 2400, 4800, 9600, 19200, 38400], index=3)

if st.button("🔌 Connetti Strumento"):
    st.session_state.tps = SokkiaDirect(port, baud)
    if st.session_state.tps.connect():
        st.success("Connesso con successo!")

if "tps" in st.session_state:
    st.markdown("---")
    
    st.subheader("Comandi di Misura")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if st.button("📏 Richiedi Angoli (00H)"):
            # 00H: Comando standard per dati angolari [cite: 10, 12]
            res = st.session_state.tps.send_command("00H")
            st.info(f"Risposta: {res}")
            
    with c2:
        if st.button("📐 Misura Distanza (11H)"):
            # 11H: Richiesta distanza e angoli [cite: 13]
            res = st.session_state.tps.send_command("11H")
            st.info(f"Risposta: {res}")

    with c3:
        if st.button("🛑 Stop Misura (12H)"):
            # 12H: Stop misura [cite: 13]
            st.session_state.tps.send_command("12H")

    st.markdown("---")
    st.subheader("Impostazioni Strumento")
    c4, c5, c6 = st.columns(3)

    with c4:
        if st.button("🔄 Azzera Angolo Oriz. (Xh)"):
            # Xh: Imposta angolo orizzontale a 0 [cite: 163]
            res = st.session_state.tps.send_command("Xh")
            st.write(f"Esito: {res}")

    with c5:
        if st.button("💡 Luci ON (Xr)"):
            # Xr: Accende illuminazione display [cite: 163]
            st.session_state.tps.send_command("Xr")
            
    with c6:
        if st.button("🌑 Luci OFF (Xs)"):
            # Xs: Spegne illuminazione display [cite: 163]
            st.session_state.tps.send_command("Xs")

    st.markdown("---")
    custom_cmd = st.text_input("Invia comando manuale (es. A per info strumento)")
    if st.button("Invia Manuale"):
        res = st.session_state.tps.send_command(custom_cmd)
        st.code(res)
