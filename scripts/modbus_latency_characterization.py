#!/usr/bin/env python3
"""
modbus_latency_characterization.py

Usage:
    python3 modbus_latency_characterization.py --cycle-ms 1 --samples 2000
    python3 modbus_latency_characterization.py --cycle-ms 0.5 --samples 2000

Arguments:
    --cycle-ms   : scan cycle time currently set in OpenPLC (ms). Used to
                   identify OS jitter events (samples > cycle_time) and
                   label output files. Must match what's set in the runtime.
    --samples    : number of trials to collect (default 2000)
    --plc-ip     : IP address of the Pi running OpenPLC (default 127.0.0.1)
    --delay-ms   : pause between trials in ms (default 10). Gives the PLC
                   time to reset the coil between cycles. Reduce for faster
                   collection, increase if you see many back-to-back timeouts.

Modbus map:
    %QW0   -> Holding register 0  (Python writes 1 to trigger, 0 to reset)
    %QX0.0 -> Coil 0              (Python reads this waiting for TRUE)

Dependencies:
    pip install pymodbus

See experiments/modbus_latency_characterization.md for full setup,
procedure, and how to interpret results.
"""

import time
import csv
import statistics
import argparse
from datetime import datetime
from pymodbus.client import ModbusTcpClient

# ── Arguments ─────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='OpenPLC Modbus latency characterization')
parser.add_argument('--cycle-ms',  type=float, default=1.0,
                    help='Scan cycle time set in OpenPLC (ms), default 1.0')
parser.add_argument('--samples',   type=int,   default=2000,
                    help='Number of trials to collect, default 2000')
parser.add_argument('--plc-ip',    type=str,   default='127.0.0.1',
                    help='IP address of Pi running OpenPLC, default 127.0.0.1')
parser.add_argument('--delay-ms',  type=float, default=10.0,
                    help='Pause between trials in ms, default 10')
args = parser.parse_args()

CYCLE_MS   = args.cycle_ms
NUM        = args.samples
PLC_IP     = args.plc_ip
DELAY_S    = args.delay_ms / 1000.0
TIMEOUT_S  = max(CYCLE_MS * 20 / 1000, 0.1)   # 20x cycle time or 100ms, whichever larger

REGISTER   = 0    # %QW0
COIL       = 0    # %QX0.0
DEVICE_ID  = 1
PORT       = 502

TIMESTAMP  = datetime.now().strftime('%Y%m%d_%H%M%S')
CSV_FILE   = f"modbus_latency_{CYCLE_MS}ms_{TIMESTAMP}.csv"
TXT_FILE   = f"modbus_latency_summary_{CYCLE_MS}ms_{TIMESTAMP}.txt"

# ── Connect ────────────────────────────────────────────────────────────────────

client = ModbusTcpClient(PLC_IP, port=PORT)
if not client.connect():
    raise RuntimeError(
        f"Could not connect to OpenPLC at {PLC_IP}:{PORT}\n"
        "Is the runtime running and Modbus server enabled?"
    )

# ── Header ─────────────────────────────────────────────────────────────────────

print()
print("=" * 62)
print("  OpenPLC Modbus Latency Characterization")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 62)
print(f"  PLC IP        : {PLC_IP}:{PORT}")
print(f"  Cycle time    : {CYCLE_MS} ms  (must match OpenPLC setting)")
print(f"  Samples       : {NUM}")
print(f"  Delay/trial   : {args.delay_ms} ms")
print(f"  Timeout/trial : {TIMEOUT_S*1000:.0f} ms")
print(f"  CSV output    : {CSV_FILE}")
print(f"  Summary       : {TXT_FILE}")
print("-" * 62)
print("  Running automatically. Progress prints every 200 samples.")
print()

# ── Verify PLC is responding ───────────────────────────────────────────────────

print("  Verifying connection...")
rr = client.read_coils(COIL, count=1, device_id=DEVICE_ID)
if rr.isError():
    raise RuntimeError(
        "Connected to Modbus server but can't read coil 0.\n"
        "Check that the PLC program is uploaded and the PLC is started."
    )

# Make sure coil starts LOW before first trial
client.write_register(REGISTER, 0, device_id=DEVICE_ID)
time.sleep(CYCLE_MS / 1000 * 2)
print("  PLC responding. Starting trials...\n")

# ── Main loop ──────────────────────────────────────────────────────────────────

results  = []   # latency_ms for successful trials
timeouts = 0
errors   = 0

for i in range(NUM):

    # Small pause between trials — gives PLC time to process the reset
    time.sleep(DELAY_S)

    # Write trigger value — start clock immediately after
    wr = client.write_register(REGISTER, 1, device_id=DEVICE_ID)
    t0 = time.perf_counter()

    if wr.isError():
        errors += 1
        continue

    # Tight-poll for coil to go TRUE — no sleep, as fast as Modbus allows
    timed_out = True
    deadline  = t0 + TIMEOUT_S
    while time.perf_counter() < deadline:
        rr = client.read_coils(COIL, count=1, device_id=DEVICE_ID)
        if not rr.isError() and rr.bits[0]:
            t1 = time.perf_counter()
            timed_out = False
            break

    # Reset: write 0 so PLC sets coil back to FALSE before next trial
    client.write_register(REGISTER, 0, device_id=DEVICE_ID)

    if timed_out:
        timeouts += 1
        continue

    latency_ms = (t1 - t0) * 1000
    results.append(latency_ms)

    # Progress every 200 samples
    if len(results) % 200 == 0 and len(results) > 1:
        m   = statistics.mean(results)
        std = statistics.stdev(results)
        mx  = max(results)
        spikes = sum(1 for x in results if x > CYCLE_MS)
        print(f"  [{len(results):>5}/{NUM}]  "
              f"mean={m:.3f}ms  std={std:.3f}ms  "
              f"max={mx:.3f}ms  spikes>{CYCLE_MS}ms: {spikes}")

client.close()

# ── Analysis ───────────────────────────────────────────────────────────────────

n = len(results)
print()

if n < 10:
    print(f"  Only {n} valid samples ({timeouts} timeouts, {errors} errors).")
    print("  PLC may be unresponsive or misconfigured. Check runtime and program.")
else:
    sorted_r = sorted(results)
    mean_ms  = statistics.mean(results)
    med_ms   = statistics.median(results)
    std_ms   = statistics.stdev(results)
    min_ms   = min(results)
    max_ms   = max(results)
    p95      = sorted_r[int(0.95 * n)]
    p99      = sorted_r[int(0.99 * n)]
    p999     = sorted_r[int(0.999 * n)] if n >= 1000 else None

    # Sigma bounds — upper bound only (we care about worst-case latency, not fast outliers)
    sigma3   = mean_ms + 3 * std_ms   # 99.73% of a normal distribution falls within this
    sigma5   = mean_ms + 5 * std_ms   # 99.99994% — essentially "almost never" for normal dist

    # Count samples outside each sigma bound
    outside3 = [x for x in results if x > sigma3]
    outside5 = [x for x in results if x > sigma5]

    # Spikes: samples above cycle_time (missed scans / OS jitter)
    spikes     = [x for x in results if x > CYCLE_MS]
    spike_pct  = len(spikes) / n * 100

    # Floor estimate: 10th percentile (bottom of distribution)
    floor_est  = sorted_r[int(0.10 * n)]

    lines = [
        "=" * 62,
        f"  Results  ({n} samples, cycle time = {CYCLE_MS} ms)",
        "-" * 62,
        f"  Floor estimate (10th pct) : {floor_est:>8.4f} ms",
        f"  Min                       : {min_ms:>8.4f} ms",
        f"  Mean                      : {mean_ms:>8.4f} ms",
        f"  Median                    : {med_ms:>8.4f} ms",
        f"  Std dev                   : {std_ms:>8.4f} ms",
        f"  Max                       : {max_ms:>8.4f} ms",
        f"  95th percentile           : {p95:>8.4f} ms",
        f"  99th percentile           : {p99:>8.4f} ms",
    ]
    if p999:
        lines.append(f"  99.9th percentile         : {p999:>8.4f} ms")

    lines += [
        "-" * 62,
        f"  3-sigma bound (mean + 3σ) : {sigma3:>8.4f} ms",
        f"    samples outside         : {len(outside3):>4}  ({len(outside3)/n*100:.2f}%)",
        f"  5-sigma bound (mean + 5σ) : {sigma5:>8.4f} ms",
        f"    samples outside         : {len(outside5):>4}  ({len(outside5)/n*100:.2f}%)",
        "-" * 62,
        f"  OS jitter events (>{CYCLE_MS}ms)  : {len(spikes):>4}  ({spike_pct:.2f}% of samples)",
        f"  Timeouts                  : {timeouts:>4}",
        f"  Errors                    : {errors:>4}",
        "-" * 62,
    ]

    # Interpretation
    lines.append("  Interpretation:")
    lines.append(f"  - Floor ~{floor_est:.3f}ms: fixed Modbus + Python overhead,")
    lines.append(f"    irreducible with this software stack regardless of cycle time.")

    expected_max = CYCLE_MS + floor_est
    lines.append(f"  - Expected max without jitter: ~{expected_max:.2f}ms")
    lines.append(f"    (floor + one full cycle). Samples above this are OS jitter.")

    if spike_pct < 1.0:
        lines.append(f"  - {spike_pct:.2f}% jitter rate — very low. OS scheduler")
        lines.append(f"    rarely preempts the PLC at this cycle time.")
    elif spike_pct < 5.0:
        lines.append(f"  - {spike_pct:.2f}% jitter rate — moderate. OS occasionally")
        lines.append(f"    misses the scan window. RT kernel may help.")
    else:
        lines.append(f"  - {spike_pct:.2f}% jitter rate — high. OS is frequently")
        lines.append(f"    preempting the PLC. This cycle time may be too aggressive")
        lines.append(f"    for standard Raspberry Pi OS.")

    if max_ms > CYCLE_MS * 5:
        lines.append(f"  - Worst case ({max_ms:.3f}ms) is {max_ms/CYCLE_MS:.1f}x the cycle time —")
        lines.append(f"    the PLC missed multiple consecutive scans at least once.")

    lines.append("=" * 62)

    for l in lines:
        print(l)
    print()

    # ── Save outputs ──────────────────────────────────────────────────────────

    with open(TXT_FILE, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['sample', 'latency_ms', 'cycle_time_ms',
                         'above_cycle_time', 'above_floor',
                         'outside_3sigma', 'outside_5sigma'])
        for idx, val in enumerate(results, start=1):
            above_cycle  = 1 if val > CYCLE_MS else 0
            above_floor  = 1 if val > floor_est * 1.5 else 0
            out3         = 1 if val > sigma3 else 0
            out5         = 1 if val > sigma5 else 0
            writer.writerow([idx, f"{val:.4f}", CYCLE_MS,
                             above_cycle, above_floor, out3, out5])

    print(f"  Summary saved to {TXT_FILE}")
    print(f"  Raw data saved to {CSV_FILE}")
    print()
