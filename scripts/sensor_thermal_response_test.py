#!/usr/bin/env python3
"""
sensor_thermal_response_test.py

Measures the thermal response time of the PT100 + MAX31865 sensing chain

What is being measured:
    physical temperature changes (plunge)
        -> MAX31865 converts resistance to digital
            -> SPI transfer to Pi
                -> Python reads the value

Trigger method:
    A GPIO pin (TRIGGER_PIN) is used as the plunge trigger.
    Bridge TRIGGER_PIN to GND at the moment of plunge to mark t0.
    The script records t0 from that GPIO event and timestamps all
    readings relative to it.

Hardware:
    - PT100 + MAX31865 wired as in the PT100 experiment (CS on GPIO5)
    - A jumper wire from TRIGGER_PIN (default GPIO26, Pin 37) to GND
      held open until the moment of plunge, then bridged

Output:
    - Live terminal output showing temperature and elapsed time
    - CSV file: sensor_response_TIMESTAMP.csv

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

# Configuration

# PT100 / MAX31865
CS_PIN       = board.D5
WIRES        = 4
RTD_NOMINAL  = 100.0       # 100.0 for PT100
REF_RESISTOR = 430.0

# Conversion mode — see module docstring. True is faster (~20-21ms vs ~52-65ms)
# but enables continuous bias current, which can cause slight self-heating of
# the RTD if left on for long periods. Fine for a single plunge test.
AUTO_CONVERT = True

# Trigger GPIO (bridge to GND at moment of plunge)
TRIGGER_PIN  = 26          # BCM numbering — Pin 37 on the 40-pin header

# Test parameters
CONVERSION_RATE_SAMPLES = 30   # readings used to measure the real per-call time
PRE_PLUNGE_SAMPLES      = 30   # samples to collect before arming (establishes baseline)
POST_PLUNGE_SECONDS     = 30   # how long to log after the plunge trigger fires
NOISE_THRESHOLD         = 0.5  # °C change from baseline needed to count as "onset"

# Output
OUTPUT_FILE = f"sensor_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# Hardware setup

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
GPIO.setup(TRIGGER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# Pin floats HIGH. Bridging to GND pulls it LOW -> that's the plunge event.

# Helpers
def read_sensor():
    """Return (temperature_C, resistance_ohms) from the PT100."""
    return sensor.temperature, sensor.resistance


def find_onset(readings, baseline, noise_threshold):
    """
    readings: list of [elapsed_ms, temp]
    Returns the index of the first sample that exceeds baseline by more
    than noise_threshold. None if not found.
    """
    for i, (_, temp) in enumerate(readings):
        if abs(temp - baseline) > noise_threshold:
            return i
    return None


def time_to_fraction(readings, baseline, final_temp, fraction):
    """
    readings: list of [elapsed_ms, temp]
    Returns elapsed_ms at which temp first reaches baseline + fraction*(step).
    fraction=0.632 -> time constant tau. fraction=0.90 -> 90% settling. etc.
    None if not reached in the data.
    """
    target = baseline + fraction * (final_temp - baseline)
    direction = 1 if final_temp > baseline else -1
    for elapsed_ms, temp in readings:
        if direction * (temp - target) >= 0:
            return elapsed_ms
    return None


def fmt_time(ms):
    """Format a millisecond value as both ms and us for readability."""
    if ms is None:
        return "n/a"
    return f"{ms:>9.2f} ms   ({ms * 1000:>10.0f} us)"


# Measure the real conversion rate

print()
print("=" * 64)
print("  PT100 Thermal Response Test  (sensor only — no PLC involved)")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 64)
print(f"  auto_convert : {AUTO_CONVERT}")
print(f"  Trigger pin  : GPIO{TRIGGER_PIN}  (Pin 37) — bridge to GND to fire")
print(f"  Output       : {OUTPUT_FILE}")
print("-" * 64)
print()
print("  Phase 0: Measuring real per-reading conversion time...")
print("           (this is the actual resolution ceiling of this sensor —")
print("            see script docstring for why this can't go below it)")
print()

conversion_times_ms = []
for i in range(CONVERSION_RATE_SAMPLES):
    t_start = time.perf_counter()
    _ = sensor.temperature
    t_end = time.perf_counter()
    conversion_times_ms.append((t_end - t_start) * 1000)

avg_conv_ms = statistics.mean(conversion_times_ms)
min_conv_ms = min(conversion_times_ms)
max_conv_ms = max(conversion_times_ms)

print(f"  Per-reading time over {CONVERSION_RATE_SAMPLES} calls:")
print(f"    Min  : {min_conv_ms:.2f} ms  ({min_conv_ms*1000:.0f} us)")
print(f"    Mean : {avg_conv_ms:.2f} ms  ({avg_conv_ms*1000:.0f} us)")
print(f"    Max  : {max_conv_ms:.2f} ms  ({max_conv_ms*1000:.0f} us)")
print()
print(f"  >> This is your real sampling resolution: ~{avg_conv_ms:.1f} ms per sample.")
print(f"  >> Any 'response time' faster than this is not measurable with")
print(f"     this sensor/library combination, regardless of loop speed.")
print()

# Baseline

print("-" * 64)
print("  Phase 1: Collecting baseline (keep sensor still in starting medium)...")
print()

baseline_readings = []
for i in range(PRE_PLUNGE_SAMPLES):
    temp, resistance = read_sensor()
    baseline_readings.append(temp)
    print(f"  [{i+1:3d}/{PRE_PLUNGE_SAMPLES}]  {temp:.3f} C   {resistance:.3f} ohm")

baseline = statistics.mean(baseline_readings)
baseline_std = statistics.stdev(baseline_readings)

print()
print(f"  Baseline : {baseline:.3f} C  (std dev = {baseline_std:.3f} C)")
if baseline_std > 0.1:
    print("  !! Baseline noise is high (>0.1 C). Consider letting the sensor")
    print("     settle longer before re-running, or check wiring/SPI noise.")
print()

# Wait for plunge trigger

print("-" * 64)
print(f"  Phase 2: Ready. Bridge GPIO{TRIGGER_PIN} -> GND the moment you plunge.")
print("           Waiting for trigger...")
print()

while GPIO.input(TRIGGER_PIN) == GPIO.HIGH:
    temp, _ = read_sensor()
    print(f"\r  Current temp: {temp:.3f} C   (waiting for trigger...)", end="")
    # Deliberately no extra delay beyond the conversion itself — this loop
    # is already bound by the ~20-65ms conversion time measured in Phase 0.

t0 = time.perf_counter()
trigger_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
print(f"\n\n  Trigger fired at {trigger_time} -- logging started!")
print()

# Log post-plunge readings

print("  Phase 3: Logging...")
print()
print(f"  {'Elapsed (ms)':>14}  {'Temp (C)':>10}  {'Resistance (ohm)':>17}")
print(f"  {'-'*14}  {'-'*10}  {'-'*17}")

post_readings = []   # list of [elapsed_ms, temp_C, resistance]
deadline = t0 + POST_PLUNGE_SECONDS

while time.perf_counter() < deadline:
    temp, resistance = read_sensor()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    post_readings.append([elapsed_ms, temp, resistance])
    print(f"  {elapsed_ms:>14.1f}  {temp:>10.3f}  {resistance:>17.3f}")
    # No sleep beyond the conversion itself -- already going as fast as the
    # chip allows. Adding sleep(0) here would do nothing; the bottleneck is
    # inside sensor.temperature, not this loop.

print()
print(f"  Collected {len(post_readings)} samples over {POST_PLUNGE_SECONDS}s")
print(f"  ({len(post_readings) / POST_PLUNGE_SECONDS:.1f} samples/sec actual)")

# Analysis

print()
print("=" * 64)
print("  Phase 4: Analysis")
print("-" * 64)

final_temps = [r[1] for r in post_readings[-10:]]
final_temp  = statistics.mean(final_temps)
step_size   = final_temp - baseline

print(f"  Baseline temp        : {baseline:.3f} C")
print(f"  Final temp           : {final_temp:.3f} C")
print(f"  Step size            : {step_size:+.3f} C")
print(f"  Measurement floor    : ~{avg_conv_ms:.1f} ms/sample (from Phase 0)")
print()

readings_2col = [[r[0], r[1]] for r in post_readings]

onset_idx = find_onset(readings_2col, baseline, NOISE_THRESHOLD)
onset_ms = post_readings[onset_idx][0] if onset_idx is not None else None
print(f"  Onset (>{NOISE_THRESHOLD} C change)")
print(f"    {fmt_time(onset_ms)}")
if onset_ms is not None and onset_ms < avg_conv_ms * 2:
    print(f"    !! Within ~2 conversion cycles of t0 -- treat with caution,")
    print(f"       this could be one sample's worth of measurement floor.")
print()

tau_ms = time_to_fraction(readings_2col, baseline, final_temp, 0.632)
print(f"  Tau (63.2% of step)")
print(f"    {fmt_time(tau_ms)}")
if tau_ms is None:
    print(f"    Not reached in logging window -- extend POST_PLUNGE_SECONDS")
print()

t90_ms = time_to_fraction(readings_2col, baseline, final_temp, 0.90)
print(f"  90% settling")
print(f"    {fmt_time(t90_ms)}")
if t90_ms is None:
    print(f"    Not reached in logging window")
print()

t95_ms = time_to_fraction(readings_2col, baseline, final_temp, 0.95)
print(f"  95% settling")
print(f"    {fmt_time(t95_ms)}")
if t95_ms is None:
    print(f"    Not reached in logging window")
print()

# Save CSV

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "sample", "elapsed_ms", "elapsed_us", "temp_c", "resistance_ohm",
        "delta_from_baseline", "pct_of_step",
    ])
    for i, (elapsed_ms, temp, resistance) in enumerate(post_readings, start=1):
        delta = temp - baseline
        pct   = (delta / step_size * 100) if step_size != 0 else 0
        writer.writerow([
            i, f"{elapsed_ms:.4f}", f"{elapsed_ms*1000:.0f}",
            f"{temp:.4f}", f"{resistance:.4f}", f"{delta:.4f}", f"{pct:.2f}",
        ])

print(f"  Results saved to {OUTPUT_FILE}")
print("=" * 64)
print()

GPIO.cleanup()
