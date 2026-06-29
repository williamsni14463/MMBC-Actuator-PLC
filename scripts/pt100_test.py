#!/usr/bin/env python3
"""
pt100_test.py

Simple sanity check for a PT100 RTD wired through an
Adafruit MAX31865 amplifier breakout to a Raspberry Pi 4.

Loops forever, printing raw resistance (Ohms) and temperature (C)
every 2 seconds. Also reports sensor fault flags so wiring problems
show up as named faults instead of confusing numbers.

Stop with Ctrl+C.

Dependencies:
    pip install adafruit-blinka adafruit-circuitpython-max31865
    (or install inside a venv — see experiment log for details)
"""

import time
import board
import digitalio
import adafruit_max31865

# --- Configuration ---
CS_PIN = board.D5          # GPIO pin wired to the sensor's CS pad
WIRES = 4                  # 2, 3, or 4 -- must match your RTD wiring
RTD_NOMINAL = 100.0        # 100.0 for PT100, 1000.0 for PT1000
REF_RESISTOR = 430.0       # 430.0 for the PT100 board, 4300.0 for PT1000
READ_INTERVAL = 2.0        # seconds between readings

# --- Setup ---
spi = board.SPI()
cs = digitalio.DigitalInOut(CS_PIN)

sensor = adafruit_max31865.MAX31865(
    spi, cs,
    wires=WIRES,
    rtd_nominal=RTD_NOMINAL,
    ref_resistor=REF_RESISTOR,
)

FAULT_NAMES = (
    "HIGHTHRESH",   # RTD resistance too high
    "LOWTHRESH",    # RTD resistance too low
    "REFINLOW",     # REFIN- low (open reference/RTD wiring)
    "REFINHIGH",    # REFIN- high
    "RTDINLOW",     # RTDIN- low (open RTD element/wiring)
    "OVUV",         # over/under voltage on the chip
)

print("PT100 / MAX31865 test starting. Press Ctrl+C to stop.\n")

# --- Main loop ---
try:
    while True:
        resistance = sensor.resistance
        temperature = sensor.temperature
        faults = sensor.fault

        print(
            f"Resistance: {resistance:7.3f} Ohms   |   "
            f"Temperature: {temperature:7.3f} C"
        )

        active_faults = [
            name for name, is_set in zip(FAULT_NAMES, faults) if is_set
        ]
        if active_faults:
            print(f"  !! Sensor fault(s): {', '.join(active_faults)}")
            sensor.clear_faults()

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("\nStopped by user.")
