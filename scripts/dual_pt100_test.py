#!/usr/bin/env python3
"""
dual_pt100_test.py

Simple live readout of TWO PT100 sensors, each on its own MAX31865 amplifier,
sharing one SPI bus on a Raspberry Pi. Use this to confirm both chamber
sensors are working.

The two amplifiers share SDI/SDO/CLK but each has its own CS (chip select):
    Sensor 1 CS -> GPIO8  (CE0, physical pin 24)
    Sensor 2 CS -> GPIO7  (CE1, physical pin 26)

Output is deliberately simple: both temperatures, both resistances, and the
difference between them, updated once a second.

Usage:
    python3 dual_pt100_test.py

Dependencies:
    pip3 install --break-system-packages adafruit-blinka
    pip3 install --break-system-packages adafruit-circuitpython-max31865

See setup/dual-pt100-test-setup.md for full wiring and pinout.
"""

import time
import board
import digitalio
import adafruit_max31865

# ── Configuration ─────────────────────────────────────────────────────────────
# For PT100 sensors on the Adafruit PT100 board:
#   RTD_NOMINAL  = 100.0   (PT100; use 1000.0 for PT1000)
#   REF_RESISTOR = 430.0   (PT100 board; use 4300.0 for PT1000 board)
# WIRES must match your sensor AND the jumper on the MAX31865 board (2, 3, or 4).

RTD_NOMINAL   = 100.0
REF_RESISTOR  = 430.0
WIRES         = 4          # set to 2, 3, or 4 to match your PT100 wiring
READ_INTERVAL = 1.0        # seconds between readings

# CS (chip select) pins — the ONLY thing that differs between the two sensors
CS_SENSOR_1 = board.D8     # GPIO8,  CE0, physical pin 24
CS_SENSOR_2 = board.D7     # GPIO7,  CE1, physical pin 26

# ── Setup ─────────────────────────────────────────────────────────────────────

# Both sensors share the same SPI bus
spi = board.SPI()

def make_sensor(cs_pin):
    cs = digitalio.DigitalInOut(cs_pin)
    return adafruit_max31865.MAX31865(
        spi, cs,
        wires=WIRES,
        rtd_nominal=RTD_NOMINAL,
        ref_resistor=REF_RESISTOR,
    )

sensor1 = make_sensor(CS_SENSOR_1)
sensor2 = make_sensor(CS_SENSOR_2)

# ── Read loop ─────────────────────────────────────────────────────────────────

print("PT100 Dual Sensor Test  —  Ctrl+C to stop")
print()

try:
    while True:
        t1 = sensor1.temperature
        r1 = sensor1.resistance
        t2 = sensor2.temperature
        r2 = sensor2.resistance
        diff = t1 - t2

        # \033[F moves the cursor up a line so the readout updates in place
        # instead of scrolling. First pass just prints normally.
        print(f"  Sensor 1 (CE0):  {t1:7.2f} °C   {r1:8.2f} Ω")
        print(f"  Sensor 2 (CE1):  {t2:7.2f} °C   {r2:8.2f} Ω")
        print(f"  Difference   :  {diff:7.2f} °C")
        print()

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("Stopped.")
