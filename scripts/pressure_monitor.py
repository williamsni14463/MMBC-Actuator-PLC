#!/usr/bin/env python3
"""
MAMBA pressure monitor
Kulite CTL-312-500A  ->  KSC-2 conditioner  ->  Industrial Shields RPi PLC (0-10 V analog input)

What it does:
  - reads the PLC's 0-10 V analog input (averaged, to knock down noise)
  - converts counts -> volts -> pressure (PSIA and atm)
  - prints all the useful numbers so you can confirm the chain is alive
  - logs everything to a timestamped CSV
  - optionally live-graphs pressure vs time  (--plot)
  - two-point calibration mode                (--calibrate)
  - hardware-free test mode                   (--sim)

Run examples:
  python3 pressure_monitor.py --probe          # just show raw counts/volts (setup aid)
  python3 pressure_monitor.py --calibrate      # capture two known pressures, save cal
  python3 pressure_monitor.py                  # monitor + log to console/CSV
  python3 pressure_monitor.py --plot           # monitor + live graph
  python3 pressure_monitor.py --sim --plot     # try the whole pipeline with fake data

Ctrl-C stops and prints a session summary.
"""

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from collections import deque
from datetime import datetime

# ======================= CONFIG — EDIT FOR YOUR SETUP =======================
PLC_VERSION = "RPIPLC_V6"     # board HARDWARE version: RPIPLC_V3 / V4 / V6.
                              # 57AAR+ is current-gen — confirm V4 vs V6 from the unit label.
PLC_MODEL   = "RPIPLC_57AAR"  # your model. librpiplc string is RPIPLC_57AAR
                              # (the trailing "+" on the label is not part of the string).
ANALOG_PIN  = "I0.2"          # the analog input terminal the KSC-2 center wire lands on

MAX_COUNTS  = 2047            # 11-bit input -> 2047.  If your board reads up to 4095,
                              # it's 12-bit: set this to 4095.  (Use --probe to check:
                              # drive the input near 9 V and see whether counts top out
                              # around 1843 [11-bit] or 3686 [12-bit].)
VREF        = 10.0            # analog input full-scale voltage (0-10 V)

# --- Sensor / conditioner nominal (only used if no calibration file exists) ---
SENSITIVITY_MV_PER_PSI = 0.203   # CTL-312-500A cal cert, at 10.0 V excitation
TOTAL_GAIN             = 202.0   # KSC-2 pregain * postgain that you actually set
                                 # nominal, balance=0, absolute: 0 PSIA -> 0 V

# --- Behavior ---
AVG_SAMPLES = 16      # readings averaged per data point (more = smoother, slower)
PERIOD_S    = 0.5     # seconds between data points
WINDOW_S    = 120     # rolling window shown on the live graph
# ===========================================================================

ATM_PER_PSI = 1.0 / 14.6959
CAL_FILE    = "pressure_cal.json"
LOG_DIR     = "pressure_logs"


# --------------------------------------------------------------------------
# Hardware access  (the only part that talks to the PLC — swap here if needed)
# --------------------------------------------------------------------------
class Reader:
    def __init__(self, sim=False):
        self.sim = sim
        self._t0 = time.time()
        if sim:
            print("[sim] hardware-free mode: generating synthetic ~6 atm signal")
            return
        try:
            from rpiplc_lib import rpiplc
        except ImportError as e:
            sys.exit(
                "ERROR: could not import rpiplc_lib.\n"
                "  Install the Industrial Shields libraries (librpiplc + python3-librpiplc),\n"
                "  or run with --sim to test the rest of the pipeline.\n"
                f"  ({e})"
            )
        self.rpiplc = rpiplc
        # Newer python3-librpiplc wants init(version, model); some pre-built installs
        # are already configured and take no args. Handle both.
        try:
            rpiplc.init(PLC_VERSION, PLC_MODEL)
        except TypeError:
            rpiplc.init()
        rpiplc.pin_mode(ANALOG_PIN, rpiplc.INPUT)

    def read_counts(self, samples=AVG_SAMPLES):
        if self.sim:
            return self._sim_counts()
        acc = 0
        for _ in range(samples):
            acc += self.rpiplc.analog_read(ANALOG_PIN)
            time.sleep(0.001)
        return acc / samples

    def _sim_counts(self):
        t = time.time() - self._t0
        psia = 6 * 14.6959 + 8.0 * math.sin(t * 0.15) + random.gauss(0, 0.4)
        volts = psia * (SENSITIVITY_MV_PER_PSI * TOTAL_GAIN / 1000.0)
        counts = volts / VREF * MAX_COUNTS
        return max(0.0, min(float(MAX_COUNTS), counts))


# --------------------------------------------------------------------------
# Conversions
# --------------------------------------------------------------------------
def counts_to_volts(counts):
    return counts / MAX_COUNTS * VREF


def nominal_cal():
    """PSIA = A*volts + B  from the datasheet (balance=0 -> B=0)."""
    slope_v_per_psi = SENSITIVITY_MV_PER_PSI * TOTAL_GAIN / 1000.0
    return {"mode": "nominal", "A": 1.0 / slope_v_per_psi, "B": 0.0}


def load_cal():
    if os.path.exists(CAL_FILE):
        with open(CAL_FILE) as f:
            c = json.load(f)
        print(f"[cal] loaded {CAL_FILE}: PSIA = {c['A']:.4f}*V + {c['B']:.4f}  ({c['mode']})")
        return c
    c = nominal_cal()
    print(f"[cal] no cal file — using NOMINAL: PSIA = {c['A']:.4f}*V + {c['B']:.4f}")
    print("      NOTE: nominal assumes zero offset. Your sensor's amplified zero-balance")
    print("      (~1 V at this gain) makes the uncalibrated reading sit HIGH. This is")
    print("      expected — run --calibrate and the two-point fit removes it.")
    return c


def volts_to_psia(volts, cal):
    return cal["A"] * volts + cal["B"]


# --------------------------------------------------------------------------
# Two-point calibration
# --------------------------------------------------------------------------
def calibrate(reader):
    print("\n=== TWO-POINT CALIBRATION ===")
    print("You need two known pressures (e.g. a barometer at atmosphere, and a")
    print("pump/reference gauge at a second value). This absorbs the sensor zero")
    print("offset, gain tolerance and ADC offset in one step.\n")
    pts = []
    for i in (1, 2):
        input(f"Point {i}: set/hold a known pressure, then press Enter to capture...")
        counts = reader.read_counts(64)
        volts = counts_to_volts(counts)
        p = float(input(f"   captured {volts:.4f} V — enter the true pressure here (PSIA): "))
        pts.append((volts, p))
        print(f"   -> point {i}: {volts:.4f} V = {p:.3f} PSIA")
    (v1, p1), (v2, p2) = pts
    if abs(v2 - v1) < 1e-6:
        sys.exit("ERROR: the two points are at (nearly) the same voltage — can't fit a line.")
    A = (p2 - p1) / (v2 - v1)
    B = p1 - A * v1
    cal = {"mode": "twopoint", "A": A, "B": B, "points": pts,
           "timestamp": datetime.now().isoformat()}
    with open(CAL_FILE, "w") as f:
        json.dump(cal, f, indent=2)
    print(f"\nSaved: PSIA = {A:.4f}*V + {B:.4f}  ->  {CAL_FILE}")
    print("Re-run without --calibrate to monitor.\n")


# --------------------------------------------------------------------------
# Range sanity check
# --------------------------------------------------------------------------
def range_flag(volts):
    if volts <= 0.02:
        return "!! ~0 V: no signal? (check Input Mode=Operate, BNC seated, excitation on)"
    if volts < 0.0:
        return "!! NEGATIVE: set KSC-2 balance to 0 (input can't read <0 V)"
    if volts >= 9.8:
        return "!! NEAR 10 V CEILING: reduce KSC-2 gain / check overpressure"
    if volts >= 9.5:
        return "!  approaching 10 V ceiling"
    return ""


# --------------------------------------------------------------------------
# Monitor loop
# --------------------------------------------------------------------------
def monitor(reader, cal, use_plot):
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(LOG_DIR, f"pressure_{stamp}.csv")
    png_path = os.path.join(LOG_DIR, f"pressure_{stamp}.png")

    plt = None
    if use_plot:
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot as plt
            plt.ion()
            fig, ax = plt.subplots(figsize=(9, 4))
            (line,) = ax.plot([], [], lw=1.4)
            ax.set_xlabel("time (s)")
            ax.set_ylabel("pressure (atm)")
            ax.set_title("MAMBA chamber pressure")
            ax.grid(True, alpha=0.3)
        except Exception as e:
            print(f"[plot] live graph unavailable ({e}); logging headless instead")
            plt = None

    t_hist, p_hist_atm = deque(), deque()
    all_atm = []
    n = 0
    t_start = time.time()

    hdr = f"{'time':>8}  {'counts':>7}  {'volts':>7}  {'PSIA':>8}  {'atm':>7}   flags"
    print("\nLogging to", csv_path)
    print(hdr)
    print("-" * len(hdr))

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["iso_time", "elapsed_s", "counts", "volts", "psia", "atm"])
        try:
            while True:
                t = time.time() - t_start
                counts = reader.read_counts()
                volts = counts_to_volts(counts)
                psia = volts_to_psia(volts, cal)
                atm = psia * ATM_PER_PSI
                flag = range_flag(volts)

                print(f"{t:8.1f}  {counts:7.1f}  {volts:7.4f}  {psia:8.2f}  {atm:7.3f}   {flag}")
                w.writerow([datetime.now().isoformat(), f"{t:.3f}", f"{counts:.1f}",
                            f"{volts:.4f}", f"{psia:.3f}", f"{atm:.4f}"])
                f.flush()

                all_atm.append(atm)
                n += 1
                if plt:
                    t_hist.append(t); p_hist_atm.append(atm)
                    while t_hist and t - t_hist[0] > WINDOW_S:
                        t_hist.popleft(); p_hist_atm.popleft()
                    line.set_data(list(t_hist), list(p_hist_atm))
                    ax.relim(); ax.autoscale_view()
                    fig.canvas.draw(); fig.canvas.flush_events()

                time.sleep(PERIOD_S)
        except KeyboardInterrupt:
            pass

    # ---- session summary ----
    dur = time.time() - t_start
    print("\n" + "=" * 48)
    print("SESSION SUMMARY")
    print("=" * 48)
    if all_atm:
        mean = sum(all_atm) / len(all_atm)
        var = sum((x - mean) ** 2 for x in all_atm) / len(all_atm)
        std = math.sqrt(var)
        print(f"  samples        : {n}")
        print(f"  duration       : {dur:.1f} s   ({n/dur:.2f} samples/s)")
        print(f"  mean pressure  : {mean:.3f} atm  ({mean/ATM_PER_PSI:.2f} PSIA)")
        print(f"  min / max      : {min(all_atm):.3f} / {max(all_atm):.3f} atm")
        print(f"  noise (std)    : {std*1000:.2f} matm  ({std/ATM_PER_PSI*1000:.2f} mPSI)")
    print(f"  CSV log        : {csv_path}")

    # save a final PNG of the whole session (works headless too)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt2
        xs = [i * PERIOD_S for i in range(len(all_atm))]
        plt2.figure(figsize=(9, 4))
        plt2.plot(xs, all_atm, lw=1.2)
        plt2.xlabel("time (s)"); plt2.ylabel("pressure (atm)")
        plt2.title(f"MAMBA chamber pressure — {stamp}")
        plt2.grid(True, alpha=0.3); plt2.tight_layout()
        plt2.savefig(png_path, dpi=130)
        print(f"  plot PNG       : {png_path}")
    except Exception as e:
        print(f"  (PNG not saved: {e})")
    print()


# --------------------------------------------------------------------------
def probe(reader):
    """Raw counts/volts stream — use this while setting MAX_COUNTS and KSC-2 gain."""
    print("PROBE mode — Ctrl-C to stop. Watch the count range as you change pressure/gain.")
    print(f"{'counts':>8}  {'volts':>8}")
    try:
        while True:
            c = reader.read_counts()
            print(f"{c:8.1f}  {counts_to_volts(c):8.4f}")
            time.sleep(0.25)
    except KeyboardInterrupt:
        print()


def main():
    ap = argparse.ArgumentParser(description="MAMBA pressure monitor (CTL-312 -> KSC-2 -> RPi PLC)")
    ap.add_argument("--sim", action="store_true", help="run without hardware (synthetic signal)")
    ap.add_argument("--calibrate", action="store_true", help="two-point calibration, then save")
    ap.add_argument("--probe", action="store_true", help="stream raw counts/volts only")
    ap.add_argument("--plot", action="store_true", help="live graph while monitoring")
    args = ap.parse_args()

    reader = Reader(sim=args.sim)

    if args.probe:
        probe(reader)
        return
    if args.calibrate:
        calibrate(reader)
        return

    cal = load_cal()
    print("\nConfig:")
    print(f"  pin={ANALOG_PIN}  max_counts={MAX_COUNTS}  vref={VREF} V")
    print(f"  avg={AVG_SAMPLES} samples/point  period={PERIOD_S}s")
    monitor(reader, cal, use_plot=args.plot)


if __name__ == "__main__":
    main()
