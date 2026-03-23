import serial
import time

try:
    ser = serial.Serial(
        port="COM11",
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=2
    )

    print("✅ CONNESSO")

    # test base
    ser.write(b"\r\n")
    time.sleep(0.5)

    ser.write(b"00D\r\n")
    time.sleep(0.5)

    response = ser.readline()
    print("RISPOSTA:", response)

    ser.close()

except Exception as e:
    print("❌ ERRORE:", e)
