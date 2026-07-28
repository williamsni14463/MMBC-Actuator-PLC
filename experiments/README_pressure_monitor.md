# Pressure monitor — run instructions

Chain: **Kulite CTL-312-500A → KSC-2 → Industrial Shields RPi PLC (0–10 V analog input)**
Script: `pressure_monitor.py`

---

## 1. One-time setup on the PLC

The Industrial Shields libraries are usually pre-installed with their OS image. If not:

```bash
sudo apt update && sudo apt install -y git python3-pip
# C library (dependency):
git clone https://github.com/Industrial-Shields/librpiplc
# then build for YOUR version+model, e.g. V6 / model 58:
cd librpiplc && cmake -B build -DPLC_VERSION=RPIPLC_V6 -DPLC_MODEL=RPIPLC_58
cmake --build build/ -- -j$(nproc) && sudo cmake --install build/ && sudo ldconfig && cd ..
# Python wrapper:
git clone https://github.com/Industrial-Shields/python3-librpiplc
cd python3-librpiplc && sudo pip3 install . && cd ..
```

For the live graph: `pip3 install matplotlib` (headless logging + PNG work without it too).

## 2. Edit the CONFIG block at the top of the script

| Constant | Set to |
|---|---|
| `PLC_VERSION`, `PLC_MODEL` | your exact board (label / librpiplc model list) |
| `ANALOG_PIN` | the input terminal the KSC-2 center wire lands on (e.g. `I0.2`) |
| `MAX_COUNTS` | `2047` if 11-bit input, `4095` if 12-bit (confirm with `--probe`) |
| `TOTAL_GAIN` | the KSC-2 pregain × postgain you actually set |

## 3. Test sequence (do these in order)

**a) Probe — confirm the input sees the signal and set MAX_COUNTS**
```bash
python3 pressure_monitor.py --probe
```
You should see steady counts and volts. Change the KSC-2 excitation 10→5 V and watch volts drop — that's the same live-chain proof you saw on the scope. Note whether counts top out near **1843** (11-bit) or **3686** (12-bit) at ~9 V and set `MAX_COUNTS` accordingly.

**b) Calibrate — two known pressures (do this for real accuracy)**
```bash
python3 pressure_monitor.py --calibrate
```
Capture at two known pressures (a barometer at atmosphere is one easy point). It saves `pressure_cal.json`, which then overrides the nominal datasheet conversion. This absorbs the sensor's ±5 mV zero offset, gain tolerance, and ADC offset in one step.

**c) Monitor**
```bash
python3 pressure_monitor.py          # console + CSV (works over SSH)
python3 pressure_monitor.py --plot   # add a live pressure-vs-time graph
```
Ctrl-C stops and prints a session summary + saves a PNG.

**No hardware yet?** `python3 pressure_monitor.py --sim --plot` exercises the whole pipeline with a synthetic ~6 atm signal.

## 4. What "working" looks like

Console columns: `time  counts  volts  PSIA  atm  flags`

- **On the bench (steady room pressure):** counts/volts/pressure sit at a **constant** value with small jitter. A flat, steady reading is correct — nothing is changing the pressure.
- **The proof it's live:** change KSC-2 excitation 10→5 V and the volts/PSIA **halve**, then return when you set it back. That confirms the signal travels sensor → DB9 → KSC-2 → PLC.
- **Sanity number:** at your gain (~202) and nominal cal, 6 atm ≈ 88 PSIA ≈ **3.6 V ≈ ~660 counts** (11-bit). If your reading lands near the pressure you expect, the conversion is right.

## 5. Flags the script raises

| Flag | Meaning / fix |
|---|---|
| `~0 V: no signal?` | Input Mode not Operate, BNC loose, or excitation off/faulted |
| `NEGATIVE` | Set KSC-2 **balance = 0** — the 0–10 V input can't read below 0 V |
| `approaching / NEAR 10 V ceiling` | Reduce KSC-2 gain, or you're near overpressure — the input maxes at 10 V |

## 6. Files produced

- `pressure_logs/pressure_<timestamp>.csv` — iso_time, elapsed_s, counts, volts, psia, atm
- `pressure_logs/pressure_<timestamp>.png` — pressure-vs-time plot of the session
- `pressure_cal.json` — saved two-point calibration

## 7. Measuring end-to-end latency (for the paper)

The dominant delay in this chain is the I²C ADC read + program cycle, not the KSC-2's µs-scale filter. To measure the *true* sensor-to-decision time, use the LC584A: pressure signal on Ch1, a PLC digital output on Ch2 that your logic toggles when the reading crosses a threshold, and read the gap between the two edges. That's a measured figure to sit alongside your 0.64 ms Modbus number.

---

> Nominal conversion uses the CTL-312-500A cal cert (0.203 mV/PSI @ 10 V) × your gain. The two-point calibration replaces it with a measured fit — use that for any number you report. Resolution ≠ accuracy: the sensor's own error (~±0.1% FSO ≈ ±0.5 PSI) is the floor regardless of ADC counts.
