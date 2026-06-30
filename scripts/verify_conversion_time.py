#!/usr/bin/env python3
"""
verify_conversion_time.py

Part 1 of 2 for the sensor response experiment.

PURPOSE:
    Verify the actual conversion cycle time of the MAX31865 amplifier
    by watching the RDY (DRDY) pin directly. This is a hardware signal
    that goes LOW the instant the chip finishes a conversion and new
    data is available. By timing pulse-to-pulse intervals on that pin
    we get the true conversion period — not a Python-level estimate,
    not a datasheet assumption, the real measured interval on this
    specific chip at room temperature.

    This answers: "Is the amplifier actually converting at ~20-21ms
    (continuous mode) or ~52-65ms (single-shot)?"

WHAT DRDY / RDY DOES:
    - Goes LOW  when a fresh conversion result is ready in the register
    - Goes HIGH when the data register is read (SPI read clears it)
    - In continuous (auto_convert) mode: pulses at a fixed rate set by
      the chip's internal filter clock (~20-21ms for 50Hz filter)
    - We measure falling-edge to falling-edge interval = one conversion
      period

WIRING (one new wire beyond normal PT100 setup):
    Adafruit breakout RDY pin  ->  GPIO25 (Pi Pin 22)

    The RDY pin is labeled "RDY" on the Adafruit breakout and sits in
    the header row alongside VIN, GND, SDO, SDI, SCK, CS.

OUTPUT:
    - Live terminal printout of each interval
    - Summary stats (min, mean, max, std dev) over N pulses
    - CSV: conversion_timing_TIMESTAMP.csv

Dependencies:
    pip install adafruit-blinka adafruit-circuitpython-max31865
    sudo apt install python3-rpi.gpio
"""

import time
import csv
import statistics
import board
import digitalio
import adafruit_max31865
import RPi.GPIO as GPIO
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────

# PT100 / MAX31865 SPI
CS_PIN       = board.D5
WIRES        = 4
RTD_NOMINAL  = 100.0
REF_RESISTOR = 430.0

# RDY pin — wire Adafruit breakout "RDY" to this GPIO
RDY_PIN      = 25     # BCM25, Pi Pin 22

# Conversion mode
AUTO_CONVERT = True   # True = ~20-21ms continuous; False = ~52-65ms single-shot

# How many falling edges (completed conversions) to measure
NUM_PULSES   = 100

OUTPUT_FILE  = f"conversion_timing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# ── Setup ─────────────────────────────────────────────────────────────────────

spi = board.SPI()
cs  = digitalio.DigitalInOut(CS_PIN)
sensor = adafruit_max31865.MAX31865(
    spi, cs,
    wires=WIRES,
    rtd_nominal=RTD_NOMINAL,
    ref_resistor=REF_RESISTOR,
)
sensor.auto_convert = AUTO_CONVERT

GPIO.setmode(GPIO.BCM)
GPIO.setup(RDY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# RDY is active-low: idles HIGH, goes LOW when conversion is done.

# ── Header ────────────────────────────────────────────────────────────────────

print()
print("=" * 60)
print("  MAX31865 Conversion Time Verification")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print(f"  RDY pin     : GPIO{RDY_PIN}  (Pi Pin 22)")
print(f"  auto_convert: {AUTO_CONVERT}")
print(f"  Pulses      : {NUM_PULSES}")
print(f"  Expected    : {'~20-21 ms' if AUTO_CONVERT else '~52-65 ms'}  (per datasheet)")
print(f"  Output      : {OUTPUT_FILE}")
print("-" * 60)
print()
print("  Waiting for first RDY pulse...")
print()
print(f"  {'Pulse':>6}  {'Interval (ms)':>14}  {'Interval (us)':>14}")
print(f"  {'-'*6}  {'-'*14}  {'-'*14}")

# ── Measurement loop ──────────────────────────────────────────────────────────
# Strategy:
#   Wait for RDY to go LOW (conversion done), then immediately read the
#   sensor over SPI — this clears DRDY and lets it go HIGH again.
#   Record the timestamp of each falling edge. Interval between
#   consecutive falling edges = one full conversion cycle.

intervals_ms = []
t_last       = None

for i in range(NUM_PULSES + 1):   # +1 because first edge gives us t_last with no interval yet

    # Wait for falling edge (RDY goes LOW)
    while GPIO.input(RDY_PIN) == GPIO.HIGH:
        pass   # busy-wait — keep latency as low as possible
    t_now = time.perf_counter()

    # Read sensor over SPI — this clears the DRDY flag so RDY goes HIGH
    # again and the chip can signal the next conversion
    _ = sensor.temperature

    if t_last is not None:
        interval_ms = (t_now - t_last) * 1000
        intervals_ms.append(interval_ms)
        print(f"  {i:>6}  {interval_ms:>14.3f}  {interval_ms*1000:>14.0f}")

    t_last = t_now

# ── Summary ───────────────────────────────────────────────────────────────────

mean_ms   = statistics.mean(intervals_ms)
median_ms = statistics.median(intervals_ms)
min_ms    = min(intervals_ms)
max_ms    = max(intervals_ms)
std_ms    = statistics.stdev(intervals_ms)

print()
print("=" * 60)
print(f"  Results  ({NUM_PULSES} intervals)")
print("-" * 60)
print(f"  Min    : {min_ms:>9.3f} ms   ({min_ms*1000:>8.0f} us)")
print(f"  Mean   : {mean_ms:>9.3f} ms   ({mean_ms*1000:>8.0f} us)")
print(f"  Median : {median_ms:>9.3f} ms   ({median_ms*1000:>8.0f} us)")
print(f"  Max    : {max_ms:>9.3f} ms   ({max_ms*1000:>8.0f} us)")
print(f"  Std dev: {std_ms:>9.3f} ms   ({std_ms*1000:>8.0f} us)")
print()

expected_ms = 20.5 if AUTO_CONVERT else 58.0
drift_pct = abs(mean_ms - expected_ms) / expected_ms * 100
print(f"  Datasheet expected : ~{expected_ms:.1f} ms")
print(f"  Measured mean      :  {mean_ms:.3f} ms")
print(f"  Difference         :  {drift_pct:.1f}%")
print()

if drift_pct < 5:
    print("  >> Chip is running at expected conversion rate.")
elif drift_pct < 15:
    print("  >> Slightly off from datasheet — could be filter frequency")
    print("     mismatch (50Hz vs 60Hz) or measurement overhead. Normal.")
else:
    print("  !! Large deviation from expected. Check:")
    print("     - Is auto_convert set correctly?")
    print("     - Is the RDY pin wired correctly (not floating)?")
    print("     - Are there SPI errors or bus conflicts?")

print()

# Record this measured mean so the thermal response script can use it
# as a verified floor rather than an assumption
with open("verified_conversion_time_ms.txt", "w") as f:
    f.write(f"{mean_ms:.4f}\n")
print(f"  Verified mean written to verified_conversion_time_ms.txt")
print(f"  (sensor_thermal_response_drdy.py will read this automatically)")

# ── Save CSV ──────────────────────────────────────────────────────────────────

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["pulse", "interval_ms", "interval_us"])
    for idx, ms in enumerate(intervals_ms, start=1):
        writer.writerow([idx, f"{ms:.4f}", f"{ms*1000:.0f}"])

print(f"  Full results saved to {OUTPUT_FILE}")
print("=" * 60)
print()

GPIO.cleanup()
