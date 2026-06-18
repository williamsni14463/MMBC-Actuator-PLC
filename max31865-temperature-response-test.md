# MAX31865 Temperature Response Test (Raspberry Pi + OpenPLC)

Measures how fast OpenPLC can detect a temperature threshold crossing and react with an output — the thermal equivalent of the button/LED latency test.

**General Overview**
- A MAX31865 breakout board reads the PT100 RTD (resistance temperature detector) sensor over SPI (a 4-wire communication protocol)
- Python will poll the sensor continuously and notes the exact moment the temperature crosses a threshold — that's t₀
- OpenPLC reads a GPIO input (driven by Python when the threshold is crossed) and turns on an output — that's t₁
- Latency = t₁ − t₀

---

## 1. Enable SPI on the Pi

SPI is disabled by default. Run this line of code to

```bash
sudo raspi-config
```

Go to **Interface Options → SPI → Enable**, then reboot the pi

Verify it is enabled with:

```bash
ls /dev/spi*
# Expected: /dev/spidev0.0  /dev/spidev0.1
```

---

## 2. Wiring

### MAX31865 → Raspberry Pi (SPI)

| MAX31865 pin | Pi pin | GPIO |
|---|---|---|
| VIN | Pin 1 | 3.3V |
| GND | Pin 6 | GND |
| SDI | Pin 19 | MOSI |
| SDO | Pin 21 | MISO |
| CLK | Pin 23 | SCLK |
| CS  | Pin 29 | GPIO5 |

### 4-wire PT100 → MAX31865 screw terminals

```
F+     RTD+    RTD−    F−
RED    RED     BLUE    BLUE
```

Both red wires go in the left two terminals, both blue wires go in the right two.

> While there are 2-3 wire configurations, the 4-wire configuration cancels out wire resistance entirely. Making it the most accurate option.

<img width="515" height="296" alt="image" src="https://github.com/user-attachments/assets/1e07919a-08e7-40fc-aa0b-db933c176731" />


### PLC output monitor tap

Tap a jumper wire in between the resistor and pin 16 jumper wire

```
Pin 16 (GPIO23) ──┬──── 330Ω ──── LED ──── GND
                  │
             Pin 18 (GPIO24)   ← Python reads this
```

### New: Python → PLC input wire

Python signals the PLC when the threshold is crossed:

```
Pin 11 (GPIO17) ──── PLC input (IX0.3)
```

Python drives GPIO17 HIGH at the threshold crossing. The PLC reads it and turns on GPIO23 (LED). GPIO24 monitors that output — same as before.

---

## 3. OpenPLC Program

No changes needed to the existing ladder logic from the last 2 examples. The same rung works:

```
|----[ IX0.3 ]----( QX0.2 )----|
```

Instead of a button driving a reaction, a change in temperature drives the system.

---

## 4. Install Dependencies

```bash
sudo pip3 install adafruit-blinka --break-system-packages
sudo pip3 install adafruit-circuitpython-max31865 --break-system-packages
```

---

## 5. Check

Before running the full test, test to see if the sensor reads correctly:

```bash
sudo python3 - <<'EOF'
import board
import digitalio
import adafruit_max31865

spi = board.SPI()
cs  = digitalio.DigitalInOut(board.D5)
sensor = adafruit_max31865.MAX31865(spi, cs, rtd_nominal=100, ref_resistor=430.0, wires=4)

print(f"Temperature: {sensor.temperature:.2f} °C")
print(f"Resistance:  {sensor.resistance:.2f} Ω")
EOF
```

> At room temperature, a PT100 should read ~20–25°C and ~107–110Ω. If the reading is wrong, check SPI is enabled and the CS wire is on Pin 29.

---

## 6. Add and Run the Script

Copy to the Pi:

```bash
scp temperature_response_test.py pi@YOUR_PI_IP:/home/pi/
```

Or paste directly into nano on the Pi:

```bash
nano ~/temperature_response_test.py
```

Make sure OpenPLC Runtime is running with the PLC started, then:

```bash
sudo python3 ~/temperature_response_test.py
```

The code sets a default threshold to 35°C. To change it:

```bash
sudo python3 ~/temperature_response_test.py --threshold 40.0
```

---

## 7. Running the Experiment

**To trigger each measurement:**
1. Put the sensor in warm/hot water — temperature rises and crosses the threshold
2. Script detects the crossing → records t₀ → waits for PLC output to switch
3. PLC reacts → LED turns on → script records t₁ → prints latency
4. Remove sensor and let it cool 2°C below threshold → repeat

---

## 8. Results

Copy CSV results to your computer:

```bash
scp pi@YOUR_PI_IP:/home/pi/temp_response_results.csv ./
```

---


## 9. Optional Arguments

```bash
# Cold water test — react when temp drops below threshold
sudo python3 ~/temperature_response_test.py --direction below --threshold 20.0

# Faster polling for tighter measurements (min ~25 ms due to sensor conversion time)
# The MAX31865 takes a maximum of 21 ms to translate the RTD resistance into a digital temperature
sudo python3 ~/temperature_response_test.py --poll-ms 25

# More samples
sudo python3 ~/temperature_response_test.py --samples 20

# Custom output file
sudo python3 ~/temperature_response_test.py --out my_results.csv
```

---

## Code

```python
"""
MAX31865 Temperature Response Test
====================================
Measures how fast the PLC can detect a temperature threshold crossing
and react by switching a GPIO output (LED or relay).

Usage:
  sudo python3 temperature_response_test.py
  sudo python3 temperature_response_test.py --threshold 35.0 --sensor pt1000 --out temp_results.csv
"""

import time
import csv
import argparse
import statistics
import sys
from datetime import datetime

import board
import digitalio
import adafruit_max31865
import RPi.GPIO as GPIO

# CLI Arguments
parser = argparse.ArgumentParser(description="Measure OpenPLC temperature threshold response time")
parser.add_argument("--threshold",  type=float, default=35.0,
                    help="Temperature threshold in °C the PLC should react to (default: 35.0)")
parser.add_argument("--direction",  choices=["above", "below"], default="above",
                    help="React when temp goes above or below threshold (default: above)")
parser.add_argument("--sensor",     choices=["pt100", "pt1000"], default="pt100",
                    help="RTD sensor type (default: pt100)")
parser.add_argument("--poll-ms",    type=float, default=50.0,
                    help="How often to read temperature in ms (default: 50)")
parser.add_argument("--timeout-s",  type=float, default=60.0,
                    help="Max seconds to wait for PLC to react after threshold crossed (default: 60)")
parser.add_argument("--samples",    type=int,   default=10,
                    help="Number of threshold crossings to measure (default: 10)")
parser.add_argument("--out",        type=str,   default="temp_response_results.csv",
                    help="Output CSV filename (default: temp_response_results.csv)")
args = parser.parse_args()

POLL_S   = args.poll_ms / 1000.0
MONITOR_PIN = 24  # GPIO24 — tapped from PLC output line

# Sensor config
if args.sensor == "pt100":
    RTD_NOMINAL  = 100.0
    REF_RESISTOR = 430.0
else:
    RTD_NOMINAL  = 1000.0
    REF_RESISTOR = 4300.0

# MAX31865 Setup
spi = board.SPI()
cs  = digitalio.DigitalInOut(board.D5)  # GPIO5, Pin 29
sensor = adafruit_max31865.MAX31865(
    spi, cs,
    rtd_nominal  = RTD_NOMINAL,
    ref_resistor = REF_RESISTOR,
    wires        = 4
)

# GPIO setup for PLC output monitor
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(MONITOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Monitor pin helper
def wait_for_plc_output(target_state, timeout_s):
    """Poll GPIO24 until PLC output matches target_state."""
    deadline = time.perf_counter() + timeout_s
    while True:
        if GPIO.input(MONITOR_PIN) == target_state:
            return True, time.perf_counter()
        if time.perf_counter() > deadline:
            return False, None

# Threshold helper
def threshold_crossed(temp):
    if args.direction == "above":
        return temp >= args.threshold
    else:
        return temp <= args.threshold

def threshold_cleared(temp):
    """Opposite condition — used to wait for temp to reset between samples."""
    if args.direction == "above":
        return temp < args.threshold - 2.0   # 2°C hysteresis
    else:
        return temp > args.threshold + 2.0

# Print header
print(f"\n{'='*56}")
print(f"  MAX31865 Temperature Response Test")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*56}")
print(f"  Sensor    : {args.sensor.upper()}")
print(f"  Threshold : {args.threshold:.1f} °C ({args.direction})")
print(f"  Poll rate : every {args.poll_ms:.0f} ms")
print(f"  Samples   : {args.samples}")
print(f"  Monitor   : GPIO{MONITOR_PIN} (Pin 18)")
print(f"  Output    : {args.out}")
print(f"{'─'*56}")

# Read starting temperature
try:
    start_temp = sensor.temperature
    print(f"  Current temp: {start_temp:.2f} °C")
except Exception as e:
    print(f"\n  ERROR reading sensor: {e}")
    print("  Check SPI is enabled and wiring is correct.")
    GPIO.cleanup()
    sys.exit(1)

print(f"\n  The test will run {args.samples} threshold crossings.")
if args.direction == "above":
    print(f"  Put sensor in WARM/HOT water to cross {args.threshold:.1f} °C")
    print(f"  Then return to COOL water to reset between samples.")
else:
    print(f"  Put sensor in COLD water to cross {args.threshold:.1f} °C")
    print(f"  Then return to WARM water to reset between samples.")
print(f"\n  Press Ctrl+C to stop early.\n")

results = []
temp_log = []   # full temperature trace for CSV

# Main loop
try:
    for i in range(args.samples):
        print(f"  [{i+1:>2}/{args.samples}]  Waiting for threshold to CLEAR first...", end="", flush=True)

        # Wait for temperature to be safely away from threshold (reset state)
        reset_deadline = time.perf_counter() + 120.0
        while True:
            temp = sensor.temperature
            if threshold_cleared(temp):
                break
            if time.perf_counter() > reset_deadline:
                print(f"\n  Timed out waiting for temp to clear threshold. Current: {temp:.2f}°C")
                sys.exit(0)
            time.sleep(POLL_S)

        print(f" cleared at {sensor.temperature:.2f}°C")
        print(f"          Now cross the threshold ({args.direction} {args.threshold:.1f}°C)...", end="", flush=True)

        # Wait for threshold crossing — record t0 at the exact moment
        crossing_deadline = time.perf_counter() + 120.0
        t0 = None
        crossing_temp = None

        while True:
            temp = sensor.temperature
            ts   = time.perf_counter()
            temp_log.append((ts, temp, i+1, "monitoring"))

            if threshold_crossed(temp):
                t0 = ts
                crossing_temp = temp
                break
            if ts > crossing_deadline:
                print(f"\n  Timed out waiting for threshold crossing. Current: {temp:.2f}°C")
                break
            time.sleep(POLL_S)

        if t0 is None:
            continue

        print(f" crossed at {crossing_temp:.2f}°C")
        print(f"          Waiting for PLC output to switch...", end="", flush=True)

        # Wait for PLC to react (GPIO24 goes HIGH)
        ok, t1 = wait_for_plc_output(GPIO.HIGH, timeout_s=args.timeout_s)

        if not ok:
            print(f"  TIMEOUT — PLC did not react within {args.timeout_s:.0f} s")
            continue

        latency_ms = (t1 - t0) * 1000.0
        results.append({
            "sample":        i + 1,
            "crossing_temp": round(crossing_temp, 3),
            "latency_ms":    round(latency_ms, 3)
        })
        print(f" reacted in {latency_ms:.1f} ms  (temp was {crossing_temp:.2f}°C)")

        # Wait for PLC output to go back LOW before next sample
        wait_for_plc_output(GPIO.LOW, timeout_s=30.0)

except KeyboardInterrupt:
    print("\n\n  Interrupted by user.")

finally:
    GPIO.cleanup()

# Summary
if not results:
    print("\n  No results collected.")
    sys.exit(0)

latencies = [r["latency_ms"] for r in results]
n       = len(latencies)
mean_ms = statistics.mean(latencies)
med_ms  = statistics.median(latencies)
min_ms  = min(latencies)
max_ms  = max(latencies)
std_ms  = statistics.stdev(latencies) if n > 1 else 0.0
p95_ms  = sorted(latencies)[int(n * 0.95)]

print(f"\n{'='*56}")
print(f"  Results  ({n} samples)")
print(f"{'─'*56}")
print(f"  Min      : {min_ms:10.1f} ms")
print(f"  Max      : {max_ms:10.1f} ms")
print(f"  Mean     : {mean_ms:10.1f} ms")
print(f"  Median   : {med_ms:10.1f} ms")
print(f"  Std dev  : {std_ms:10.1f} ms")
print(f"  95th pct : {p95_ms:10.1f} ms")
print(f"{'='*56}\n")

print("  Note: latency here includes BOTH the temperature polling interval")
print(f"  ({args.poll_ms:.0f} ms) AND the PLC scan cycle (~20 ms).")
print(f"  Min achievable with {args.poll_ms:.0f} ms polling ≈ {args.poll_ms + 20:.0f} ms total.\n")

# Data to CSV
with open(args.out, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sample", "crossing_temp_c", "latency_ms"])
    for r in results:
        writer.writerow([r["sample"], r["crossing_temp"], r["latency_ms"]])
    writer.writerow([])
    writer.writerow(["stat", "value"])
    for label, val in [("min_ms", min_ms), ("max_ms", max_ms), ("mean_ms", mean_ms),
                        ("median_ms", med_ms), ("std_dev_ms", std_ms), ("p95_ms", p95_ms),
                        ("samples", n), ("threshold_c", args.threshold),
                        ("poll_interval_ms", args.poll_ms), ("sensor", args.sensor)]:
        writer.writerow([label, val])

print(f"  Saved to: {args.out}\n")
```
