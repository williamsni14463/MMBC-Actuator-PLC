#!/usr/bin/env python3
"""
sensor_thermal_response_drdy.py

Part 2 of 2 for the sensor response experiment.

PURPOSE:
    Measure the thermal lag of the PT100 + MAX31865 sensing chain by
    logging temperature only on confirmed fresh conversions (via the
    RDY pin), while using the water surface itself as the trigger for t0.

THE TWO PROBLEMS THIS SOLVES vs. the previous version:

    Problem 1 — Human timing error (GND vs. dip order):
        The old trigger required two simultaneous hand movements: dip
        the sensor AND bridge a separate jumper wire. Any gap between
        those two actions (even 50-100ms) would shift onset by that
        same amount, which is why onset values were jumping around
        wildly between trials.

        Fix: the trigger wire now runs FROM the sensor housing into
        the water bath. The water is conductive. When the sensor enters
        the water, it closes the circuit automatically — no second hand
        movement. t0 is the moment of water entry, period.

    Problem 2 — Stale reads:
        The old loop called sensor.temperature on a timer. There was no
        guarantee the chip had a fresh conversion ready — we might be
        reading the same value twice, which looks like no temperature
        change when really we just asked too soon.

        Fix: every read is gated on the RDY pin. We busy-wait for
        RDY to go LOW (conversion done), then immediately read. Every
        single data point in the log is a fresh, unique conversion.

WHAT IS BEING MEASURED:
    physical temperature changes (water entry)
        -> PT100 resistance changes
            -> MAX31865 ADC picks it up in the next conversion
                -> Python reads confirmed-fresh value

    The gap between t0 (water entry) and "first sample that moved" is
    the combined dead time of:
      - However much of the current conversion window had already
        elapsed when the sensor entered the water (0 to 1 conversion
        period, random)
      - The thermal time constant of the PT100 wire itself
      - Any Python/SPI read overhead

    This is NOT measuring PLC latency. No OpenPLC, no Modbus.

WIRING:
    Existing PT100 wiring stays exactly as-is.

    Two new wires:
      1. RDY pin (Adafruit breakout labeled "RDY")  ->  GPIO25 (Pin 22)
      2. Trigger: a bare wire attached to the sensor housing (or
         taped alongside the PT100 probe), with its other end connected
         to any GND pin on the Pi (e.g. Pin 39).
         The water bath acts as the conductor — when the sensor enters
         the water, the wire end in the water connects to GND through
         the water, pulling TRIGGER_PIN LOW.

    TRIGGER_PIN defaults to GPIO26 (Pin 37) — same as before, but now
    driven by the water rather than a separate hand.

    The water must be slightly conductive (tap water is fine; distilled
    water won't work). Test the trigger circuit before running the
    experiment: dip just the trigger wire in the water and confirm the
    terminal prints "Trigger test: LOW" not "HIGH".

OUTPUT:
    - Live terminal readout of each fresh-conversion reading
    - Analysis: onset, tau (63.2%), 90%, 95% settling
    - CSV: thermal_response_TIMESTAMP.csv

    If verify_conversion_time.py has been run first, its output file
    (verified_conversion_time_ms.txt) is read automatically and used
    as the floor reference in the analysis. If not found, falls back
    to the datasheet estimate.

Dependencies:
    pip install adafruit-blinka adafruit-circuitpython-max31865
    sudo apt install python3-rpi.gpio
"""

import time
import csv
import os
import statistics
import board
import digitalio
import adafruit_max31865
import RPi.GPIO as GPIO
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────

# PT100 / MAX31865
CS_PIN       = board.D5
WIRES        = 4
RTD_NOMINAL  = 100.0
REF_RESISTOR = 430.0
AUTO_CONVERT = True    # must match what verify_conversion_time.py used

# RDY pin
RDY_PIN      = 25      # BCM25, Pi Pin 22

# Trigger pin — pulled LOW by water when sensor enters bath
TRIGGER_PIN  = 26      # BCM26, Pi Pin 37

# Test parameters
PRE_PLUNGE_SAMPLES  = 30    # fresh conversions to collect for baseline
POST_PLUNGE_SECONDS = 30    # how long to log after trigger fires
NOISE_THRESHOLD     = 0.5   # deg C above baseline to count as onset

OUTPUT_FILE = f"thermal_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# ── Load verified conversion time if available ────────────────────────────────

VERIFIED_FLOOR_FILE = "verified_conversion_time_ms.txt"
if os.path.exists(VERIFIED_FLOOR_FILE):
    with open(VERIFIED_FLOOR_FILE) as f:
        verified_floor_ms = float(f.read().strip())
    floor_source = f"measured ({VERIFIED_FLOOR_FILE})"
else:
    verified_floor_ms = 20.5 if AUTO_CONVERT else 58.0
    floor_source = "datasheet estimate (run verify_conversion_time.py first for measured value)"

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
GPIO.setup(RDY_PIN,     GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(TRIGGER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ── Helpers ───────────────────────────────────────────────────────────────────

def wait_for_fresh_reading():
    """
    Block until RDY goes LOW (chip has a fresh conversion ready),
    read the sensor to clear RDY, then timestamp.
    Timestamp is taken AFTER the read so intervals represent
    "end of read N -> end of read N+1" — the real rate at which
    fresh data is available, consistent with verify_conversion_time.py.
    """
    while GPIO.input(RDY_PIN) == GPIO.HIGH:
        pass
    temp = sensor.temperature
    res  = sensor.resistance
    t    = time.perf_counter()   # after read, not before
    return temp, res, t


def find_onset(readings_2col, baseline, threshold):
    for i, (_, temp) in enumerate(readings_2col):
        if abs(temp - baseline) > threshold:
            return i
    return None


def time_to_fraction(readings_2col, baseline, final_temp, fraction):
    target    = baseline + fraction * (final_temp - baseline)
    direction = 1 if final_temp > baseline else -1
    for elapsed_ms, temp in readings_2col:
        if direction * (temp - target) >= 0:
            return elapsed_ms
    return None


def fmt(ms):
    if ms is None:
        return "not reached in logging window"
    return f"{ms:.2f} ms  ({ms*1000:.0f} us)"

# ── Header ────────────────────────────────────────────────────────────────────

print()
print("=" * 64)
print("  PT100 Thermal Response Test  (DRDY-gated, water trigger)")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 64)
print(f"  RDY pin      : GPIO{RDY_PIN}  (Pin 22)")
print(f"  Trigger pin  : GPIO{TRIGGER_PIN}  (Pin 37) — pulled LOW by water")
print(f"  auto_convert : {AUTO_CONVERT}")
print(f"  Conv. floor  : {verified_floor_ms:.2f} ms  [{floor_source}]")
print(f"  Output       : {OUTPUT_FILE}")
print("-" * 64)

# ── Trigger circuit test ──────────────────────────────────────────────────────

print()
print("  Trigger test: dip ONLY the trigger wire in the water to confirm")
print("  it pulls the pin LOW. Result should be LOW, not HIGH.")
time.sleep(1.0)
state = "LOW (good)" if GPIO.input(TRIGGER_PIN) == GPIO.LOW else "HIGH (not triggered yet — ok if wire is out of water)"
print(f"  Trigger pin currently: {state}")
print()

# ── Phase 1: Baseline ─────────────────────────────────────────────────────────

print("-" * 64)
print(f"  Phase 1: Collecting {PRE_PLUNGE_SAMPLES} baseline readings")
print("           (sensor in starting medium, don't move it)")
print()

# Discard first conversion — same mode-transition artifact as in
# verify_conversion_time.py: the first RDY pulse after auto_convert
# is enabled runs at single-shot speed (~52ms), not continuous speed.
print("  Discarding first conversion (mode transition artifact)...")
while GPIO.input(RDY_PIN) == GPIO.HIGH:
    pass
_ = sensor.temperature
print()

print(f"  {'#':>4}  {'Temp (C)':>10}  {'Resistance (ohm)':>17}")
print(f"  {'-'*4}  {'-'*10}  {'-'*17}")

baseline_temps = []
for i in range(PRE_PLUNGE_SAMPLES):
    temp, res, _ = wait_for_fresh_reading()
    baseline_temps.append(temp)
    print(f"  {i+1:>4}  {temp:>10.3f}  {res:>17.3f}")

baseline     = statistics.mean(baseline_temps)
baseline_std = statistics.stdev(baseline_temps)

print()
print(f"  Baseline : {baseline:.3f} C  (std dev = {baseline_std:.4f} C)")
if baseline_std > 0.1:
    print("  !! Noise is high. Let the sensor settle and re-run baseline.")
print()

# ── Phase 2: Arm and wait for water trigger ───────────────────────────────────

print("-" * 64)
print("  Phase 2: Ready.")
print()
print("  Lower the sensor (and its attached trigger wire) into the hot")
print("  water. The circuit closes through the water the instant the")
print("  sensor enters — no second hand movement needed.")
print()
print("  Waiting for trigger (TRIGGER_PIN to go LOW)...")
print()

# Show live temperature while waiting — each reading gated on RDY
while GPIO.input(TRIGGER_PIN) == GPIO.HIGH:
    temp, _, _ = wait_for_fresh_reading()
    print(f"\r  Current temp: {temp:.3f} C", end="")

t0 = time.perf_counter()
trigger_ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
print(f"\n\n  Trigger fired at {trigger_ts} — logging started!")
print()

# ── Phase 3: Log post-plunge readings (DRDY-gated) ───────────────────────────

print("  Phase 3: Logging (every reading is a confirmed fresh conversion)...")
print()
print(f"  {'Elapsed (ms)':>14}  {'Temp (C)':>10}  {'Resistance (ohm)':>17}")
print(f"  {'-'*14}  {'-'*10}  {'-'*17}")

post_readings = []   # [elapsed_ms, temp_C, resistance_ohm]
deadline      = t0 + POST_PLUNGE_SECONDS

while time.perf_counter() < deadline:
    temp, res, t_read = wait_for_fresh_reading()
    elapsed_ms = (t_read - t0) * 1000
    post_readings.append([elapsed_ms, temp, res])
    print(f"  {elapsed_ms:>14.2f}  {temp:>10.3f}  {res:>17.3f}")

n_samples   = len(post_readings)
actual_rate = n_samples / POST_PLUNGE_SECONDS
print()
print(f"  Collected {n_samples} samples over {POST_PLUNGE_SECONDS}s")
print(f"  ({actual_rate:.1f} samples/sec  =  {1000/actual_rate:.1f} ms/sample average)")
print()

# Sanity check — actual rate vs verified floor
if abs((1000/actual_rate) - verified_floor_ms) > verified_floor_ms * 0.2:
    print("  !! Actual sample rate differs from conversion floor by >20%.")
    print("     Something may be adding overhead (SPI errors, CPU load).")
    print("     Check dmesg for SPI errors.")
    print()

# ── Phase 4: Analysis ─────────────────────────────────────────────────────────

print("=" * 64)
print("  Phase 4: Analysis")
print("-" * 64)

final_temp  = statistics.mean([r[1] for r in post_readings[-10:]])
step_size   = final_temp - baseline

print(f"  Baseline            : {baseline:.4f} C")
print(f"  Final (last 10 avg) : {final_temp:.4f} C")
print(f"  Step size           : {step_size:+.4f} C")
print(f"  Conversion floor    : {verified_floor_ms:.2f} ms  [{floor_source}]")
print()

r2 = [[r[0], r[1]] for r in post_readings]

onset_idx = find_onset(r2, baseline, NOISE_THRESHOLD)
onset_ms  = post_readings[onset_idx][0] if onset_idx is not None else None
print(f"  Onset  (>{NOISE_THRESHOLD} C change)")
print(f"    {fmt(onset_ms)}")
if onset_ms is not None and onset_ms < verified_floor_ms * 2:
    print(f"    !! Within ~2 conversion cycles of t0 -- this may be noise")
    print(f"       from conversion timing, not real thermal movement. Run")
    print(f"       multiple trials and compare.")
print()

tau_ms = time_to_fraction(r2, baseline, final_temp, 0.632)
print(f"  Tau    (63.2% of step)")
print(f"    {fmt(tau_ms)}")
print()

t90_ms = time_to_fraction(r2, baseline, final_temp, 0.90)
print(f"  90%    settling")
print(f"    {fmt(t90_ms)}")
print()

t95_ms = time_to_fraction(r2, baseline, final_temp, 0.95)
print(f"  95%    settling")
print(f"    {fmt(t95_ms)}")
print()

if None in (tau_ms, t90_ms, t95_ms):
    print("  >> Some metrics not reached. Extend POST_PLUNGE_SECONDS and re-run.")
    print()

# ── Save CSV ──────────────────────────────────────────────────────────────────

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "sample", "elapsed_ms", "elapsed_us", "temp_c",
        "resistance_ohm", "delta_from_baseline", "pct_of_step",
    ])
    for i, (elapsed_ms, temp, res) in enumerate(post_readings, start=1):
        delta = temp - baseline
        pct   = (delta / step_size * 100) if step_size != 0 else 0
        writer.writerow([
            i, f"{elapsed_ms:.4f}", f"{elapsed_ms*1000:.0f}",
            f"{temp:.4f}", f"{res:.4f}", f"{delta:.4f}", f"{pct:.2f}",
        ])

print(f"  Results saved to {OUTPUT_FILE}")
print("=" * 64)
print()

GPIO.cleanup()
