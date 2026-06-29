# PT100 + OpenPLC Reaction-Time Project — Progress Log

> Living document. Append new dated entries to the **Changelog** at the bottom as the project continues. Sections 1–8 describe the system as currently built and working.

---

## 1. Project Goal

Measure how fast an OpenPLC Runtime v3 program can react to a real-world
temperature change sensed by a PT100 RTD, by:

1. Reading a PT100 on a Raspberry Pi 4 via a MAX31865 amplifier (SPI).
2. Streaming that temperature into OpenPLC over Modbus TCP.
3. Letting an OpenPLC ST program compare it to a threshold and flip a coil.
4. Timing, in Python, the round trip from "threshold crossed" to "coil confirmed ON."

This does **not** test the PT100's thermal response time; this measures how long it takes for the PLC to send an output, in this case changing a coil to true, after a temperature threshold is surpassed.

---

## 2. Hardware

### 2.1 Parts
- Raspberry Pi 4
- Adafruit MAX31865 RTD-to-digital amplifier
- PT100 RTD 

### 2.2 Wiring (Pi 40-pin header → MAX31865)

| Raspberry Pi | MAX31865 |
|---|---|
| 3V3 | VIN |
| GND | GND |
| MOSI / GPIO10 | SDI |
| MISO / GPIO9 | SDO |
| SCLK / GPIO11 | CLK |
| GPIO5 | CS |

The slots RDY and 3V3 should be left empty.

PT100 wired 4-wire into the MAX31865 screw terminals.

<img width="520" height="426" alt="image" src="https://github.com/user-attachments/assets/f0d605ca-b9ef-4eb7-afd5-5f36c8915357" />


---

## 3. Software Environment

### 3.1 OS-level setup
```bash
sudo raspi-config        # Interface Options -> SPI -> Enable -> reboot pi
ls /dev/spidev*          # confirm that /dev/spidev0.0 and /dev/spidev0.1 exist
```

### 3.2 Python packages

Raspberry Pi OS (Bookworm-based) ships with an "externally managed environment"
pip guard, so installs need either `--break-system-packages` or a venv.

```bash
pip3 install --break-system-packages --upgrade adafruit-blinka
pip3 install --break-system-packages adafruit-circuitpython-max31865
pip3 install --break-system-packages pymodbus
```

If this doesn't work, create an environment:

```bash
python3 -m venv temp-env
source temp-env/bin/activate
```

Then install the dependancies inside of this environment:

```bash
pip install --upgrade pip
pip install adafruit-blinka
pip install adafruit-circuitpython-max31865
```

Keep in mind if you go this route (I did), you **NEED** to open this environment whenever you run your python code because the dependancies are installed inside of it.

Always open the environment with
```bash
source temp-env/bin/activate
```

Then you can run your code:
```bash
python3 your_script.py
```

### 3.3 OpenPLC
- OpenPLC Editor (used to write/compile the ST program)
- OpenPLC Runtime v3 (running on the Pi or another host on the same network), web UI on port 8080, Modbus TCP server on port 502

---

## 4. Phase 1 — PT100 Check

Before involving OpenPLC at all, confirm the sensor and wiring work on their own.

### 4.1 Script: `pt100_test.py`

```python
#!/usr/bin/env python3
"""
pt100_test.py

Simple script for a PT100 RTD wired through an
Adafruit MAX31865 amplifier breakout to a Raspberry Pi 4.

It loops forever, printing the raw resistance in Ohms and the
converted temperature (C) every couple of seconds, and also reports
any sensor fault flags so wiring problems are obvious.

Stop with Ctrl+C.
"""

import time
import board
import digitalio
import adafruit_max31865

# CONFIGURATION - change these to match your hardware

CS_PIN = board.D5          # GPIO pin wired to the sensor's CS pad
WIRES = 4                  # 2, 3, or 4 -- must match your RTD wiring
RTD_NOMINAL = 100.0        # 100.0 for PT100, 1000.0 for PT1000
REF_RESISTOR = 430.0       # 430.0 for the PT100 board, 4300.0 for PT1000
READ_INTERVAL = 2.0        # seconds between readings

# SETUP

spi = board.SPI()
cs = digitalio.DigitalInOut(CS_PIN)

sensor = adafruit_max31865.MAX31865(
    spi,
    cs,
    wires=WIRES,
    rtd_nominal=RTD_NOMINAL,
    ref_resistor=REF_RESISTOR,
)

FAULT_NAMES = (
    "HIGHTHRESH",   # RTD resistance too high
    "LOWTHRESH",    # RTD resistance too low
    "REFINLOW",     # REFIN- low (open reference/RTD wiring)
    "REFINHIGH",    # REFIN- high
    "RTDINLOW",     # RTDIN- low (open RTD element/wiring)
    "OVUV",         # over/under voltage on the chip
)

print("PT100 / MAX31865 test starting. Press Ctrl+C to stop.\n")

# MAIN LOOP

try:
    while True:
        resistance = sensor.resistance
        temperature = sensor.temperature
        faults = sensor.fault  # 6-tuple of booleans

        print(
            f"Resistance: {resistance:7.3f} Ohms   |   "
            f"Temperature: {temperature:7.3f} C"
        )

        active_faults = [
            name for name, is_set in zip(FAULT_NAMES, faults) if is_set
        ]
        if active_faults:
            print(f"  !! Sensor fault(s): {', '.join(active_faults)}")
            sensor.clear_faults()

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("\nStopped by user.")
```

### 4.2 What it does
- Opens the Pi's hardware SPI bus and a `digitalio` pin for CS.
- Every `READ_INTERVAL` seconds, reads `sensor.resistance` (raw RTD ohms) and `sensor.temperature` 
- Reads `sensor.fault`, a 6-tuple of booleans corresponding to the MAX31865's fault register, and prints which (if any) are set, so a wiring problem shows up as a named fault instead of a confusing number.

### 4.3 How results were interpreted
- PT100s read ~100 Ω at 0°C, climbing ~0.385 Ω/°C — so ~108–110 Ω at room temperature is the expected baseline
- An issue I constantly ran into was the temperature reading -242.02°C, and near 0 resistance. If this is happening, one possible issue is the wiring, make sure no pins are soldered together and no connections are shorting.
- If the room temperature reading is around ~23°C, then you should be in a good place. Put your finger on the sensor and see if the temperature begins to rise.

---

## 5. Phase 2 — OpenPLC Integration

### 5.1 Modbus addressing decision

OpenPLC's Modbus TCP server maps PLC memory to standard Modbus tables

| OpenPLC location | Modbus table | Read/Write over Modbus |
|---|---|---|
| `%IX` / `%IW` | Discrete Inputs / Input Registers | **Read-only** — Modbus has no write function code for these tables |
| `%QX` | Coils | Read/Write |
| `%QW` | Holding Registers | Read/Write |
| `%MW` | Holding Registers (higher address range) | Read/Write (in theory) |

Implication: Python **cannot** write a sensor value into `%IW`/`%IX` over Modbus — those tables are read-only by protocol design, not just by convention. `%MW` looked like the semantically "correct" place for incoming sensor data, but there are real-world reports of `%MW` not updating reliably inside the ST/LD program on some OpenPLC Runtime builds, even though it writes fine over Modbus.

**Decision:** use `%QW0` for the incoming temperature value, and `%QX0.0` (a coil) for the PLC's response. Nothing else in the program writes to `%QW0`, so there's no conflict despite the conventional "output" naming.

### 5.2 Final Modbus map for this project

| Location | Modbus type | Address | Written by | Read by |
|---|---|---|---|---|
| `%QW0` | Holding Register | 0 | Python | OpenPLC program |
| `%QX0.0` | Coil | 0 | OpenPLC program | Python |

---

## 6. Phase 2 — OpenPLC Program

### 6.1 Structured Text code

```iecst
  VAR
    Threshold : INT := 3000;
    TemperatureScaled : INT AT %QW0;
    OutputBit : BOOL AT %QX0.0;
  END_VAR

IF TemperatureScaled >= Threshold THEN
    OutputBit := TRUE;
ELSE
    OutputBit := FALSE;
END_IF;
```

`Threshold` is an integer because the temperature is sent scaled ×100 (so 30.00°C → 3000) to preserve two decimal places over a 16-bit integer register.

### 6.2 Deployment steps
1. OpenPLC Editor → New Project → blank project.
2. Change the cycle time to 1ms
3. Set the main POU's language to Structured Text, paste the code section from VAR through END_VAR in the variable header by selecting this button:
   <img width="987" height="298" alt="image" src="https://github.com/user-attachments/assets/a595b9b8-110d-4815-8433-07f597061638" />
4. Paste the body of the code, IF through END_IF, in the main section
5. Select Configuration in the top left"
   <img width="236" height="287" alt="image" src="https://github.com/user-attachments/assets/8d07eef9-8d69-4b12-9d6d-41f8eb22d65c" />
6. Select Device as OpenPLC Runtime v3 and enter the IP Address of the PI found from 'hostname -I'
7. Connect to the runtime
8. In the runtime, **Settings → Hardware** → set correctly to Blank for Linux (see Section 8 — this step is where the project's main bug originated).
9. Build the project with clean build and upload in the Editor (generates a `.st` file and automatically uploads it to the runtime
   <img width="222" height="113" alt="image" src="https://github.com/user-attachments/assets/efffc3ab-6e53-4f46-8263-f4e34d84e4c5" />
10. OpenPLC Runtime web UI → **Settings → Modbus Server → Enable** (port 502).
11. Dashboard → **Start PLC** if not already started
12. Go to **Monitoring** to monitor the value of OutputBit as the python program runs

---

## 7. Phase 3 — Latency Test Script

### 7.1 Code: `openplc_reaction_time_test.py`

```python
#!/usr/bin/env python3
"""
OpenPLC Reaction Time Test
Measures the latency from:
    Python detects PT100 >= threshold
        ->
    Python writes temperature to OpenPLC via Modbus
        ->
    OpenPLC sets OutputBit
        ->
    Python detects OutputBit
This measures:
    Modbus write +
    PLC scan +
    Modbus read
NOT the PT100 thermal response time.
"""
import time
import board
import digitalio
import adafruit_max31865
from pymodbus.client import ModbusTcpClient

# PT100 Configuration

CS_PIN = board.D5          # GPIO5
WIRES = 2                  # Change to 3 if using a 3-wire RTD
RTD_NOMINAL = 100.0
REF_RESISTOR = 430.0

# OpenPLC Configuration

PLC_IP = "127.0.0.1"
PLC_PORT = 502
DEVICE_ID = 1
TEMP_REGISTER = 0          # %QW0
OUTPUT_COIL = 0            # %QX0.0

# Test Parameters

THRESHOLD_C = 30.0
SCALE = 100
THRESHOLD_INT = int(THRESHOLD_C * SCALE)
HYSTERESIS = 1.0

# Initialize PT100

spi = board.SPI()
cs = digitalio.DigitalInOut(CS_PIN)
sensor = adafruit_max31865.MAX31865(
    spi,
    cs,
    wires=WIRES,
    rtd_nominal=RTD_NOMINAL,
    ref_resistor=REF_RESISTOR,
)

# Connect to OpenPLC

client = ModbusTcpClient(PLC_IP, port=PLC_PORT)
if not client.connect():
    raise RuntimeError("Could not connect to OpenPLC.")
print()
print("Connected to OpenPLC")
print(f"Threshold = {THRESHOLD_C:.2f} C")
print("Waiting for threshold crossing...\n")
armed = True
last_written = None
try:
    while True:
        temp = sensor.temperature
        scaled = int(round(temp * SCALE))
        scaled = max(0, min(scaled, 65535))
        # Only write if changed
        if scaled != last_written:
            client.write_register(
                TEMP_REGISTER,
                scaled,
                device_id=DEVICE_ID,
            )
            last_written = scaled
        print(
            f"\rTemp = {temp:6.2f} C   "
            f"Resistance = {sensor.resistance:7.2f} ohms",
            end=""
        )
        if armed and temp >= THRESHOLD_C:
            print("\nThreshold reached!")
            # Start timing immediately before writing threshold value
            t0 = time.perf_counter()
            client.write_register(
                TEMP_REGISTER,
                scaled,
                device_id=DEVICE_ID,
            )
            while True:
                rr = client.read_coils(
                    OUTPUT_COIL,
                    count=1,
                    device_id=DEVICE_ID,
                )
                if not rr.isError() and rr.bits[0]:
                    latency_ms = (
                        time.perf_counter() - t0
                    ) * 1000
                    print(
                        f"PLC Output ON   "
                        f"Latency = {latency_ms:.3f} ms\n"
                    )
                    armed = False
                    break
        elif (not armed) and temp < (THRESHOLD_C - HYSTERESIS):
            print("Re-armed.\n")
            armed = True
        time.sleep(0.001)
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    client.close()
```

### 7.2 Walkthrough

**Setup:**
- `CS_PIN`, `WIRES`, `RTD_NOMINAL`, `REF_RESISTOR` — same MAX31865 config as Phase 1.
- `PLC_IP = "127.0.0.1"` — assumes OpenPLC Runtime is running on the same Pi as this script. Change to the Runtime's actual IP if it's on a different machine.
        • I ended up just using the actual Pi IP. Find this with 'hostname -I' in the pi terminal
- `TEMP_REGISTER` / `OUTPUT_COIL` are both address `0`, corresponding to `%QW0` and `%QX0.0` per the map in Section 5.2.
- `THRESHOLD_C` / `SCALE` must match the `Threshold` constant in the ST program exactly (30.00°C × 100 = 3000).
- `HYSTERESIS` — how far temperature must drop below the threshold before the script "re-arms" and is willing to time another crossing. Prevents one shaky reading right at the threshold from generating dozens of spurious latency readings.
      • I was only able to test it a few times, but usually waiting 10 seconds or so rearms the sensor. Just had to make sure it is cooling between attempts

**Main loop:**
1. Read `sensor.temperature`, scale and clamp it to a valid unsigned 16-bit value (`0–65535`) for the Modbus register.
2. **Write-on-change**: only sends a Modbus write if the scaled value actually changed since last loop, cutting down on redundant Modbus traffic when the temperature is stable.
3. Prints a single self-overwriting status line (`\r` + `end=""`) showing live temperature and resistance, so the terminal doesn't scroll on every iteration.
4. **Crossing detection:** if `armed` and `temp >= THRESHOLD_C`, this is the first scan where it crossed.
   - `t0` is captured *before* the timed write — note this write happens again here unconditionally (even if Section 2's write-on-change already sent this exact value), to guarantee the timer starts at the exact write that's being measured, decoupled from the caching logic above.
   - It then tight-polls `read_coils` in a `while True` loop with no sleep, checking as fast as possible for `%QX0.0` to go `True`.
   - The instant it does, `t1` is captured and `latency_ms` is printed. This is the number being tracked for this whole project.
   - `armed` is set `False` so it won't re-trigger on every subsequent scan while still above threshold.
5. **Re-arm:** once temperature drops back below `THRESHOLD_C - HYSTERESIS`, `armed` is set back to `True`, allowing another timed crossing on the next heat-up.
6. `time.sleep(0.001)` — a 1 ms loop delay, much tighter than earlier drafts, since SPI reads are fast and writes are now skipped when unchanged.

**Known limitation (intentional, not a bug):** unlike an earlier draft, this version has no timeout on the inner `read_coils` polling loop — if the PLC program is stopped or never reacts, the script will hang there indefinitely rather than reporting a failure. Worth keeping in mind during testing, make sure the sensor is actually working. When I tested the program, I opened another terminal and ran the pt100_test.py from above at the same time, just to make sure it wasn't failing in the background.

---

## 8. Issue Log

### Issue #1 — Sensor reads 0 Ω / -242°C immediately after starting the OpenPLC Runtime program

**Symptom:**
I could see that the PT100 readings are correct (Section 4.3) right up until the OpenPLC program is started ("Start PLC"). Immediately afterward, the sensor reports 0 Ω resistance and ~-242°C. Stopping the PLC program does **not** fix it. Only unplugging/repowering the Pi restores correct readings, until the PLC is started again which then it breaks again.

**Diagnostic**
1. Hypothesis: I think that OpenPLC's GPIO handling for the Pi conflicts with the SPI bus the MAX31865 needs.
2. I checked the pin states with `pinctrl`  for GPIO 5, 7, 8, 9, 10, 11 — once with the PLC stopped, once right after starting it:

| Pin | Role | State *before* Start PLC | State *after* Start PLC |
|---|---|---|---|
| GPIO5 | MAX31865 CS | output, HIGH | **input**, HIGH |
| GPIO7 | SPI0 CE1 | output, HIGH (idle) | output, **LOW** |
| GPIO8 | SPI0 CE0 | output, HIGH (idle) | output, **LOW** |
| GPIO9 | SPI0 MISO | SPI function, LOW | **input**, LOW |
| GPIO10 | SPI0 MOSI | SPI function, HIGH | **input**, HIGH |
| GPIO11 | SPI0 SCLK | SPI function, LOW | **input**, HIGH |

The moment "Start PLC" is pressed, every one of these pins changes function. GPIO5 (the sensor's own CS pin) and the entire SPI0 bus (7, 8, 9, 10, 11) get reassigned away from SPI/Blinka control.

**Root cause:**
Setting the runtime's hardware layer as Raspberry Pi forces a hardcoded set of GPIO pins as plain digital inputs or outputs as soon as the PLC starts up, which ios independant of anything written in the actual ST program. These hardcoded pins included GPIO 5,9,10,11, which were claimed as inputs, and GPIO 7,8, claimed as outputs. This explains why only a power cycle fixes everything, the GPIO function registers are rebooted when the pi reloads the SPI device tree.

**How I fixed it:**
This project's design never needs OpenPLC to touch real Pi GPIO — all data exchange happens through Modbus registers (`%QW0`, `%QX0.0`), which are pure software values regardless of the hardware layer. So:

1. OpenPLC Web UI → **Settings → Hardware**.
2. Change the hardware layer from **Raspberry Pi** to **Blank for Linux** — specifically the Linux-flavored blank option, not just the generic "Blank" entry which tries to compile the program for Windows.
3. Restart the runtime.

**Status:** Fix applied. ✅ Sensor no longer breaks on PLC start.

---

## 9. Current Status

- [x] PT100 + MAX31865 wiring confirmed working
- [x] OpenPLC Modbus server enabled, ST program deployed
- [x] Latency test script working end-to-end
- [x] GPIO/SPI conflict bug (Issue #1) found, root-caused, and fixed
- [ ] Re-collect latency measurements post-fix (multiple trials, log distribution below)

---

## 10. Changelog

**2026-06-29**
- Diagnosed and fixed Issue #1 (GPIO/SPI conflict from OpenPLC's Raspberry Pi hardware layer) using `pinctrl` before/after comparison.
- Switched OpenPLC hardware layer to "Blank for Linux."
- Updated latency test script to write-on-change, removed fixed loop delay in favor of 1 ms polling, switched pymodbus keyword to `device_id` to match pymodbus version 3.13
