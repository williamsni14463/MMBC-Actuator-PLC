# Experiment: PT100 & MAX31865 Thermal Response Time

> Living document — append new dated entries to the Changelog at the bottom.

---

## 1. What This Is Measuring

This measures the MAX31865 sensor lag, this script talks to the MAX31865 directly over SPI without the use of OpenPLC

```
real temp changes → sensor reports it

```

This is a deliberately different question from the PLC latency experiment (`pt100_openplc_progress_log.md`), which measured how fast OpenPLC reacts to a value that's already sitting in a register. There's no PLC in this test, so there's nothing to count cycles of.

What's actually being measured is the combined latency of:
1. The PT100 wire physically heating or cooling (thermal mass)
2. The MAX31865 converting the new resistance to a digital value
3. The SPI transfer to the Pi
4. Python reading the register

All four collapse into one number per fraction of the step: onset, τ (63.2%), 90% settling, 95% settling.

---

## 2. Resolution Ceiling — Read This Before Running Anything

Our goal for this project was to achieve microsecond response time. After some research, I found a hard physical limit at ~50ms. I found a couple ways to hopefully get it down to ~20-21ms, but that's the ceiling.

**The MAX31865 chip itself is the bottleneck, not the Python loop. So even if the loop cycled at a max frequency, it wouldn't matter.**

- Single-shot conversion (the library's default mode): ~52ms with 60Hz noise filtering, ~62.5ms with 50Hz filtering
- Continuous/auto-convert mode: ~20–21ms per conversion (50Hz filter) — faster, but still tens of milliseconds

Every call to `sensor.temperature` waits on one of these conversions happening inside the chip.

**What this means:** with this sensor, you cannot get response data with better than ~20ms resolution, and realistically closer to ~50-60ms unless `auto_convert` is enabled. Microsecond-resolution thermal response data is not achievable with this hardware.


### If microsecond resolution is a hard requirement

We would need to look into buying something else, I did some research and found a few possible options:
- An RTD amplifier with a faster ADC than the MAX31865 (check conversion time specs before buying.
- A thermocouple instead of an RTD, paired with a faster amplifier; thermocouples themselves can have faster thermal response
- Reading the RTD's analog output directly with a fast ADC, bypassing a packaged conversion chip's internal timing entirely

---

## 3. Why the Trigger Wire Matters

You need a `t0` for "plunge occurred" that's independent of the sensor, since the sensor is the thing being timed.

**GPIO26 (Pin 37)** is bridged to GND at the exact moment of plunge. The script detects that LOW event and marks it as `t0`.

### Wiring the trigger

```
Pin 37 (GPIO26) ──── [hold open until plunge] ──── GND (any GND pin)
```

Hold the two ends apart while the script is waiting. The instant you plunge the sensor, bridge the wire ends together. The script fires immediately.

---

## 4. Hardware Setup

Same wiring as the PT100 latency experiment, plus the trigger wire.

| Pi Pin | GPIO | Role |
|--------|------|------|
| 1      | 3V3  | MAX31865 VIN |
| 6      | GND  | MAX31865 GND |
| 19     | GPIO10 (MOSI) | MAX31865 SDI |
| 21     | GPIO9  (MISO) | MAX31865 SDO |
| 23     | GPIO11 (SCLK) | MAX31865 CLK |
| 29     | GPIO5  | MAX31865 CS |
| 37     | GPIO26 | Plunge trigger (bridge to GND) |
| 39     | GND  | Trigger return |

---

## 5. Software

**Script:** [`scripts/sensor_thermal_response_test.py`](../scripts/sensor_thermal_response_test.py)

**Dependencies:**

```
pip install adafruit-blinka adafruit-circuitpython-max31865
sudo apt install python3-rpi.gpio
```

If using a venv, activate it first:
```
source my-env/bin/activate
```

### Conversion mode

At the top of the script:

```python
AUTO_CONVERT = True
```

`True` enables continuous conversion mode (~20-21ms/sample instead of ~52-65ms). The tradeoff is that the bias current stays on continuously, which can cause slight self-heating of the RTD over long periods — not a concern for a single plunge test that runs for 30 seconds, but worth turning off (`False`) if you ever leave the sensor running unattended for hours.

---

## 6. Running the Test

### 6.1 Setup

- Two containers: one with the starting medium (room-temp water or air), one with the step medium (hot water, ~50-60°C delta is plenty)
- Trigger jumper wire ready but NOT bridged

### 6.2 Conversion rate measurement 

The script first takes 30 readings back-to-back and times each one. This runs automatically at startup — no action needed, just watch it print your real sampling resolution:

```
Phase 0: Measuring real per-reading conversion time...

  Per-reading time over 30 calls:
    Min  : 19.84 ms  (19840 us)
    Mean : 20.31 ms  (20310 us)
    Max  : 21.02 ms  (21020 us)

  >> This is the sampling resolution: ~20.3 ms per sample.
  >> Any 'response time' faster than this is not measurable with
     this sensor/library combination, regardless of loop speed.
```

### 6.3 Baseline collection

Keep the sensor still in its starting medium. The script collects 30 readings and reports the mean and standard deviation:

```
Baseline : 23.441 C  (std dev = 0.031 C)
```

Low std dev (under ~0.1°C) means the sensor is stable. If it's noisy, let it settle longer and re-run.

### 6.4 Arm and plunge

The script waits, showing a live reading:
```
Current temp: 23.441 C   (waiting for trigger...)
```

In one motion: lower the sensor into the hot water AND bridge the trigger wire. The script fires the instant the pin goes LOW:
```
Trigger fired at 11:42:03.847 -- logging started!
```

### 6.5 Logging

Logs for 30 seconds (configurable) at the conversion-limited rate measured in Phase 0. Keep the sensor submerged and still.

### 6.5 Analysis

Printed automatically, with every time shown in both ms and µs:

```
  Onset (>0.5 C change)
       214.30 ms   (    214300 us)

  Tau (63.2% of step)
      1840.70 ms   (   1840700 us)

  90% settling
      4230.10 ms   (   4230100 us)

  95% settling
      5910.40 ms   (   5910400 us)
```

Note the µs column exists for consistency with the project's eventual goal, but given the ~20ms measurement floor from Phase 0, none of these numbers actually carry microsecond-level meaning — they're millisecond-resolution numbers expressed in a smaller unit, not microsecond-resolution measurements. The script will say so directly if onset comes out suspiciously close to the floor.

Results also save to `sensor_response_TIMESTAMP.csv`.

---

## 7. Configuration Reference

```python
AUTO_CONVERT             = True   # faster (~20ms) vs default (~52-65ms)
CONVERSION_RATE_SAMPLES  = 30     # Phase 0 sample count
PRE_PLUNGE_SAMPLES       = 30     # baseline sample count
POST_PLUNGE_SECONDS      = 30     # logging window after plunge
NOISE_THRESHOLD          = 0.5    # C — set to ~3x baseline std dev
```

If analysis says "not reached in logging window," increase `POST_PLUNGE_SECONDS`.

---

## 8. Things That Can Go Wrong

**Trigger fires before the plunge:** `t0` is wrong, onset looks artificially long. Re-run.

**Onset flagged as "within 2 conversion cycles":** This is the script telling you the apparent onset might just be measurement noise from the conversion floor, not real sensor movement. Don't report this number as real latency without more trials.

**Baseline std dev is high (>0.1°C):** Sensor isn't settled, let the sensor sit, re-run.

**90%/95% settling not reached:** Extend `POST_PLUNGE_SECONDS`. PT100s in still liquid can take 10+ seconds to fully settle.

**Phase 0 numbers don't match datasheet at all:** Something else is using the SPI bus or competing for CPU. Check `dmesg` for SPI errors, confirm nothing else has the bus open.

---

## 9. Current Status

- [ ] First trial run completed
- [ ] Multiple trials collected for repeatability
- [ ] Phase 0 conversion floor confirmed consistent across runs
- [ ] Decision made on whether 20ms resolution is acceptable or a faster sensor/amplifier is needed

---

