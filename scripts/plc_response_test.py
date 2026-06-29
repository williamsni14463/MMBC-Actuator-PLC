#!/usr/bin/env python3
"""
plc_response_test.py

Measures how quickly an OpenPLC program responds to a button press
by physically monitoring the LED output line.

Hardware setup:
  - Button on GPIO17 (Pin 11)
  - LED on GPIO23 (Pin 16), via 220Ω resistor
  - Monitor tap on GPIO24 (Pin 18) — jumper from GPIO23 side of resistor

See experiments/openplc-response-time-test.md for full setup instructions.

Usage:
    sudo python3 plc_response_test.py
"""

import RPi.GPIO as GPIO
import time
import csv
import statistics
from datetime import datetime

# --- Configuration ---
BUTTON_PIN = 17       # GPIO17, Pin 11
MONITOR_PIN = 24      # GPIO24, Pin 18 — monitors the LED output line
NUM_SAMPLES = 50
OUTPUT_FILE = "plc_latency_results.csv"
TIMEOUT_S = 5.0       # max seconds to wait for LED response per press

# --- Setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.OUT)    # Python drives the button signal
GPIO.setup(MONITOR_PIN, GPIO.IN)    # Python reads the LED line

results = []

print()
print("=" * 52)
print("  OpenPLC Response Time Test")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 52)
print(f"  Button  : GPIO{BUTTON_PIN}  (Pin 11)")
print(f"  Monitor : GPIO{MONITOR_PIN}  (Pin 18)")
print(f"  Samples : {NUM_SAMPLES}")
print(f"  Output  : {OUTPUT_FILE}")
print("-" * 52)
print(f"  Press the button {NUM_SAMPLES} times when prompted.")
print("  Wait for the LED to turn off between each press.")
print()

i = 0
while i < NUM_SAMPLES:
    input(f"[{i+1:3d}/{NUM_SAMPLES:3d}]  Press the button...")

    # Simulate button press
    GPIO.output(BUTTON_PIN, GPIO.HIGH)
    t0 = time.perf_counter()

    # Wait for LED to turn on
    deadline = t0 + TIMEOUT_S
    led_on = False
    while time.perf_counter() < deadline:
        if GPIO.input(MONITOR_PIN) == GPIO.HIGH:
            t1 = time.perf_counter()
            led_on = True
            break

    GPIO.output(BUTTON_PIN, GPIO.LOW)

    if not led_on:
        print("  [timeout — skipping this press, try again]")
        continue

    latency_ms = (t1 - t0) * 1000
    print(f"  {latency_ms:.3f} ms")
    results.append(latency_ms)

    # Wait for LED to turn off before next press
    while GPIO.input(MONITOR_PIN) == GPIO.HIGH:
        time.sleep(0.001)

    i += 1

GPIO.cleanup()

# --- Summary ---
print()
print("=" * 52)
print(f"  Results  ({NUM_SAMPLES} samples)")
print("-" * 52)
print(f"  Min      : {min(results):8.3f} ms")
print(f"  Max      : {max(results):8.3f} ms")
print(f"  Mean     : {statistics.mean(results):8.3f} ms")
print(f"  Median   : {statistics.median(results):8.3f} ms")
print(f"  Std dev  : {statistics.stdev(results):8.3f} ms")
sorted_results = sorted(results)
p95 = sorted_results[int(0.95 * len(sorted_results)) - 1]
print(f"  95th pct : {p95:8.3f} ms")
print("=" * 52)
print()

# --- Save to CSV ---
with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sample", "latency_ms"])
    for idx, val in enumerate(results, start=1):
        writer.writerow([idx, f"{val:.3f}"])

print(f"Results saved to {OUTPUT_FILE}")
