"""
PLC Response Time Test
=========================================
Measures latency between button press and LED activation

Usage:
  sudo python3 plc_response_test.py
"""

import RPi.GPIO as GPIO
import time
import csv
import argparse
import statistics
import sys
from datetime import datetime

# Pin config
BUTTON_PIN  = 17   # GPIO17 BCM — PLC input
MONITOR_PIN = 24   # GPIO24 BCM — tapped from LED output line

# CLI args
parser = argparse.ArgumentParser(description="Measure OpenPLC input→output latency")
parser.add_argument("--samples",     type=int,   default=50,
                    help="Number of presses to record (default: 50)")
parser.add_argument("--out",         type=str,   default="plc_latency_results.csv",
                    help="Output CSV filename (default: plc_latency_results.csv)")
parser.add_argument("--timeout-ms",  type=float, default=2000.0,
                    help="Max wait for LED response per sample in ms (default: 2000)")
args = parser.parse_args()

TIMEOUT_S = args.timeout_ms / 1000.0

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN,  GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(MONITOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Polling Helper
def wait_for_pin(pin, target_state, timeout_s):
    """Poll a pin until it hits target_state. Returns (True, timestamp) or (False, None)."""
    deadline = time.perf_counter() + timeout_s
    while True:
        if GPIO.input(pin) == target_state:
            return True, time.perf_counter()
        if time.perf_counter() > deadline:
            return False, None

# Test loop
print(f"\n{'='*52}")
print(f"  OpenPLC Response Time Test")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*52}")
print(f"  Button  : GPIO{BUTTON_PIN}  (Pin 11)")
print(f"  Monitor : GPIO{MONITOR_PIN}  (Pin 18)")
print(f"  Samples : {args.samples}")
print(f"  Output  : {args.out}")
print(f"{'─'*52}")
print(f"  Press the button {args.samples} times when prompted.")
print(f"  Wait for the LED to turn off between each press.\n")

results = []

try:
    for i in range(args.samples):
        print(f"  [{i+1:>3}/{args.samples}]  Press the button...", end="", flush=True)

        while GPIO.input(BUTTON_PIN)  == GPIO.HIGH: time.sleep(0.005)
        while GPIO.input(MONITOR_PIN) == GPIO.HIGH: time.sleep(0.005)
        time.sleep(0.05)  # short settle

        ok, _ = wait_for_pin(BUTTON_PIN, GPIO.HIGH, timeout_s=30.0)
        if not ok:
            print("\n  No button press detected in 30 s. Exiting.")
            break

        # Records t0 immediately after detecting the press
        t0 = time.perf_counter()

        # Poll monitor pin until PLC responded
        ok, t1 = wait_for_pin(MONITOR_PIN, GPIO.HIGH, timeout_s=TIMEOUT_S)

        if not ok:
            print(f"  TIMEOUT — no LED response within {args.timeout_ms:.0f} ms, skipping")
            # wait for button release before retrying
            while GPIO.input(BUTTON_PIN) == GPIO.HIGH: time.sleep(0.005)
            continue

        latency_ms = (t1 - t0) * 1000.0
        results.append(latency_ms)
        print(f"  {latency_ms:7.3f} ms")

        # Wait for button release before next sample
        while GPIO.input(BUTTON_PIN) == GPIO.HIGH: time.sleep(0.005)
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n  Interrupted.")

finally:
    GPIO.cleanup()

# Summary
if not results:
    print("\n  No results collected.")
    sys.exit(0)

n       = len(results)
mean_ms = statistics.mean(results)
med_ms  = statistics.median(results)
min_ms  = min(results)
max_ms  = max(results)
std_ms  = statistics.stdev(results) if n > 1 else 0.0
p95_ms  = sorted(results)[int(n * 0.95)]

print(f"\n{'='*52}")
print(f"  Results  ({n} samples)")
print(f"{'─'*52}")
print(f"  Min      : {min_ms:8.3f} ms")
print(f"  Max      : {max_ms:8.3f} ms")
print(f"  Mean     : {mean_ms:8.3f} ms")
print(f"  Median   : {med_ms:8.3f} ms")
print(f"  Std dev  : {std_ms:8.3f} ms")
print(f"  95th pct : {p95_ms:8.3f} ms")
print(f"{'='*52}\n")

# Export to a CSV
with open(args.out, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sample", "latency_ms"])
    for idx, val in enumerate(results, start=1):
        writer.writerow([idx, f"{val:.4f}"])
    writer.writerow([])
    writer.writerow(["stat", "value_ms"])
    for label, val in [("min", min_ms), ("max", max_ms), ("mean", mean_ms),
                        ("median", med_ms), ("std_dev", std_ms), ("p95", p95_ms),
                        ("samples", n)]:
        writer.writerow([label, f"{val:.4f}"])

print(f"  Saved to: {args.out}\n")
