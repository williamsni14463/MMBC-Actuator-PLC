#!/usr/bin/env python3
"""
openplc_reaction_time_test.py

Measures the end-to-end latency from a PT100 temperature crossing a threshold
to OpenPLC confirming its output coil is ON.

Timing path measured:
    Python detects PT100 >= threshold
        -> Python writes temperature to OpenPLC via Modbus
        -> OpenPLC sets OutputBit (coil %QX0.0)
        -> Python detects OutputBit

This measures: Modbus write + PLC scan + Modbus read
NOT the PT100 thermal response time.

Dependencies:
    pip install adafruit-blinka adafruit-circuitpython-max31865 pymodbus
    (or install inside a venv — see experiment log for details)

See experiments/RND_pt100_openplc_progress_log.md for full setup,
OpenPLC program code, and Modbus map.
"""

import time
import board
import digitalio
import adafruit_max31865
from pymodbus.client import ModbusTcpClient

# --- PT100 Configuration ---
CS_PIN = board.D5
WIRES = 4
RTD_NOMINAL = 100.0
REF_RESISTOR = 430.0

# --- OpenPLC Configuration ---
PLC_IP = "127.0.0.1"   # change to Pi's actual IP if script runs on a different machine
PLC_PORT = 502
DEVICE_ID = 1
TEMP_REGISTER = 0       # %QW0 — Python writes temperature here
OUTPUT_COIL = 0         # %QX0.0 — OpenPLC flips this when threshold is crossed

# --- Test Parameters ---
THRESHOLD_C = 30.0      # must match Threshold constant in the ST program (×100 = 3000)
SCALE = 100             # multiply °C by this to send as integer over 16-bit register
THRESHOLD_INT = int(THRESHOLD_C * SCALE)
HYSTERESIS = 1.0        # °C below threshold before re-arming

# --- Initialize PT100 ---
spi = board.SPI()
cs = digitalio.DigitalInOut(CS_PIN)
sensor = adafruit_max31865.MAX31865(
    spi, cs,
    wires=WIRES,
    rtd_nominal=RTD_NOMINAL,
    ref_resistor=REF_RESISTOR,
)

# --- Connect to OpenPLC ---
client = ModbusTcpClient(PLC_IP, port=PLC_PORT)
if not client.connect():
    raise RuntimeError("Could not connect to OpenPLC. Is the runtime running?")

print()
print("Connected to OpenPLC")
print(f"Threshold = {THRESHOLD_C:.2f} C")
print("Waiting for threshold crossing...\n")

armed = True
last_written = None

try:
    while True:
        temp = sensor.temperature
        scaled = int(round(temp * SCALE))
        scaled = max(0, min(scaled, 65535))  # clamp to valid 16-bit unsigned range

        # Only write if value changed — avoids redundant Modbus traffic
        if scaled != last_written:
            client.write_register(TEMP_REGISTER, scaled, device_id=DEVICE_ID)
            last_written = scaled

        print(
            f"\rTemp = {temp:6.2f} C   "
            f"Resistance = {sensor.resistance:7.2f} ohms",
            end=""
        )

        if armed and temp >= THRESHOLD_C:
            print("\nThreshold reached!")
            # Start timing right before the timed write
            t0 = time.perf_counter()
            client.write_register(TEMP_REGISTER, scaled, device_id=DEVICE_ID)

            # Tight-poll for the coil to flip — no sleep, as fast as possible
            while True:
                rr = client.read_coils(OUTPUT_COIL, count=1, device_id=DEVICE_ID)
                if not rr.isError() and rr.bits[0]:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    print(f"PLC Output ON   Latency = {latency_ms:.3f} ms\n")
                    armed = False
                    break
            # Note: no timeout on the inner loop — if the PLC never reacts, this hangs.
            # Run pt100_test.py in a second terminal to confirm the sensor is alive.

        elif (not armed) and temp < (THRESHOLD_C - HYSTERESIS):
            print("Re-armed.\n")
            armed = True

        time.sleep(0.001)  # 1ms loop delay

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    client.close()
