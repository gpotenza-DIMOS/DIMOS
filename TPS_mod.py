# TPS_mod.py
import streamlit as st
import time
import serial
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class SokkiaIXController:
    """Controller per Sokkia iX-1200 via seriale"""
    def __init__(self, port='/dev/ttyUSB0', baudrate=38400, timeout=5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connect()

    def connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            st.success(f"Connesso a {self.port}")
        except Exception as e:
            st.error(f"Errore connessione seriale: {e}")
            self.ser = None

    def _send_command(self, command):
        if not self.ser or not self.ser.is_open: return None
        try:
            self.ser.write(f"00{command}\r\n".encode('ascii'))
            time.sleep(0.1)
            return self.ser.readline().decode('ascii').strip()
        except Exception as e:
            st.error(f"Errore invio comando {command}: {e}")
            return None

    def measure_full(self):
        raw = self._send_command("D")
        if not raw: return None
        try:
            parts = raw.split()
            data = {}
            for p in parts:
                if ':' in p:
                    k, v = p.split(':')
                    data[k.strip()] = float(v)
            return data
        except:
            return {"raw": raw}

    def get_tilt(self):
        raw = self._send_command("GT")
        if not raw: return None
        try:
            parts = raw.split()
            tilt = {}
            for p in parts:
                if ':' in p:
                    k, v = p.split(':')
                    tilt[k.strip()] = float(v)
            return tilt
        except:
            return {"raw": raw}

# --- Funzione Streamlit per monitoraggio ---
def run_tps_monitoring():
    st.title("TPS Monitoring - Sokkia iX-1200")
    st.markdown("Controllo e monitoraggio in tempo reale della stazione totale.")

    stazione = SokkiaIXController(port='/dev/ttyUSB0')

    if stazione.ser:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Misura Completa"):
                data = stazione.measure_full()
                st.write("Misura:", data)
        with col2:
            if st.button("Tilt"):
                tilt = stazione.get_tilt()
                st.write("Tilt:", tilt)
