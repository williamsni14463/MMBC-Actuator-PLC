#!/usr/bin/env python3
"""
verify_conversion_time.py

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

# ── Warmup — discard first conversion ────────────────────────────────────────
# The first RDY pulse after auto_convert is enabled is always slow (~52ms)
# because the chip finishes whatever single-shot conversion it was already
# in the middle of before settling into continuous mode. Waiting through
# one extra read here means the measurement loop only sees steady-state
# continuous-mode intervals.

print("  Discarding first conversion (mode transition artifact)...")
while GPIO.input(RDY_PIN) == GPIO.HIGH:
    pass
_ = sensor.temperature
print("  Done. Starting measurement loop.")
print()

# ── Measurement loop ──────────────────────────────────────────────────────────
# Strategy:
#   Wait for RDY to go LOW (conversion done), then read the sensor over
#   SPI to clear DRDY. Timestamp AFTER the read, not before.
#
#   Why after: timestamping before the read means the interval includes
#   the time from "edge detected" to "edge detected next time", minus
#   however long the SPI read took. That makes intervals slightly shorter
#   than the true conversion period because the chip starts its next
#   conversion while we're still doing the SPI transaction.
#
#   Timestamping after gives "end of read N -> end of read N+1" which is
#   the real rate at which fresh data becomes available to the script —
#   consistent and repeatable, and what actually matters for the thermal
#   response test.

intervals_ms = []
t_last       = None

for i in range(NUM_PULSES + 1):   # +1 because first iteration gives t_last with no interval yet

    # Wait for RDY to go LOW (conversion complete)
    while GPIO.input(RDY_PIN) == GPIO.HIGH:
        pass   # busy-wait — keep latency as low as possible

    # Read sensor over SPI — clears DRDY so chip can signal next conversion
    _ = sensor.temperature

    # Timestamp AFTER the read
    t_now = time.perf_counter()

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
