# Experiment: PT100 OpenPLC Reaction Time

## 1. Project Goal

Measure how fast an OpenPLC Runtime v3 program can react to a real-world temperature change sensed by a PT100 RTD, by:

1. Reading a PT100 on a Raspberry Pi 4 via a MAX31865 amplifier (SPI).
2. Streaming that temperature into OpenPLC over Modbus TCP.
3. Letting an OpenPLC ST program compare it to a threshold and flip a coil.
4. Timing, in Python, the round trip from "threshold crossed" to "coil confirmed ON."

This does **not** test the PT100's thermal response time — it measures how long it takes for the PLC to send an output (changing a coil to true) after a temperature threshold is surpassed.

---

## 2. Hardware

### 2.1 Parts

- Raspberry Pi 4
- Adafruit MAX31865 RTD-to-digital amplifier
- PT100 RTD

### 2.2 Wiring (Pi 40-pin header → MAX31865)

| Raspberry Pi  | MAX31865 |
|---------------|----------|
| 3V3           | VIN      |
| GND           | GND      |
| MOSI / GPIO10 | SDI      |
| MISO / GPIO9  | SDO      |
| SCLK / GPIO11 | CLK      |
| GPIO5         | CS       |

The RDY and 3V3 slots on the MAX31865 should be left empty.

PT100 wired 4-wire into the MAX31865 screw terminals.

<img width="518" height="418" alt="image" src="https://github.com/user-attachments/assets/c6ffbddc-1938-4a5e-8517-3d9c08527f90" />

---

## 3. Software Environment

### 3.1 OS-level setup

```
sudo raspi-config        # Interface Options -> SPI -> Enable -> reboot
ls /dev/spidev*          # confirm /dev/spidev0.0 and /dev/spidev0.1 exist
```

### 3.2 Python packages

Raspberry Pi OS (Bookworm) ships with a pip guard for "externally managed environments" — installs need either `--break-system-packages` or a venv.

```
pip3 install --break-system-packages --upgrade adafruit-blinka
pip3 install --break-system-packages adafruit-circuitpython-max31865
pip3 install --break-system-packages pymodbus
```

If that doesn't work, create a virtual environment:

```
python3 -m venv temp-env
source temp-env/bin/activate
```

Then install inside it:

```
pip install --upgrade pip
pip install adafruit-blinka
pip install adafruit-circuitpython-max31865
```

**Important:** If you go the venv route (I did), you need to re-activate the environment every time you open a new terminal session before running any scripts:

```
source temp-env/bin/activate
python3 your_script.py
```

### 3.3 OpenPLC

- OpenPLC Editor (on computer — used to write/compile the ST program)
- OpenPLC Runtime v3 (on the Pi), web UI at port 8080, Modbus TCP server at port 502

---

## 4. Phase 1 — PT100 Sanity Check

Before involving OpenPLC at all, confirm the sensor and wiring work on their own.

### 4.1 Script: `pt100_test.py`

→ **[scripts/pt100_test.py](../scripts/pt100_test.py)**

### 4.2 What it does

- Opens the Pi's hardware SPI bus and a `digitalio` pin for CS.
- Every `READ_INTERVAL` seconds, reads resistance (raw RTD ohms) and temperature.
- Reads the fault register and prints any active faults by name — makes wiring problems obvious.

### 4.3 How to interpret results

- PT100s read ~100 Ω at 0°C, climbing ~0.385 Ω/°C — so ~108–110 Ω at room temperature is normal.
- **Reading -242.02°C with near-0 resistance?** That's almost always a wiring issue. Check that no pins are shorted or soldered together.
- If you're getting ~23°C, you're good. Touch the sensor with your finger and watch the temperature rise — confirms it's actually working.

---

## 5. Phase 2 — OpenPLC Integration

### 5.1 Modbus addressing decision

OpenPLC's Modbus TCP server maps PLC memory to standard Modbus tables:

| OpenPLC location | Modbus table | Read/Write over Modbus |
|-----------------|--------------|----------------------|
| `%IX` / `%IW`   | Discrete Inputs / Input Registers | **Read-only** — no Modbus write function for these |
| `%QX`           | Coils | Read/Write |
| `%QW`           | Holding Registers | Read/Write |
| `%MW`           | Holding Registers (higher range) | Read/Write (in theory) |

Key implication: Python **cannot** write a sensor value into `%IW`/`%IX` over Modbus — those tables are read-only by protocol design. `%MW` looked like the right place semantically, but there are real-world reports of it not updating reliably inside the ST program on some OpenPLC Runtime builds.

**Decision:** Use `%QW0` for the incoming temperature value, and `%QX0.0` (a coil) for the PLC's response. Nothing else in the program writes to `%QW0`, so there's no conflict despite the "output" naming.

### 5.2 Final Modbus map for this project

| Location | Modbus type | Address | Written by | Read by |
|----------|-------------|---------|------------|---------|
| `%QW0`   | Holding Register | 0 | Python | OpenPLC program |
| `%QX0.0` | Coil | 0 | OpenPLC program | Python |

---

## 6. Phase 2 — OpenPLC Program

### 6.1 Structured Text code

```
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

`Threshold` is an integer because temperature is sent scaled ×100 (30.00°C → 3000) to preserve two decimal places over a 16-bit integer register.

### 6.2 Deployment steps

1. OpenPLC Editor → New Project → blank project.
2. Change the cycle time to 1ms.
3. Set the main POU's language to Structured Text.
4. In the variable declaration section (the header area, activated with the variables button), paste everything from `VAR` through `END_VAR`.
5. In the main code section, paste the body from `IF` through `END_IF`.
6. Go to **Device → Configuration** in the top left.
7. Set Device to **OpenPLC Runtime v3**, enter the Pi's IP address from `hostname -I`.
8. Connect to the runtime.
9. In the runtime, go to **Settings → Hardware** → set to **Blank for Linux** (NOT "Raspberry Pi" — see Issue #1 below).
10. Build with **Clean Build** and upload in the Editor — this generates and uploads the `.st` file automatically.
11. In the runtime web UI, go to **Settings → Modbus Server → Enable** (port 502).
12. Go to **Dashboard → Start PLC** if it isn't already running.
13. Go to **Monitoring** and watch `OutputBit` while the Python script runs.

---

## 7. Phase 3 — Latency Test Script

### 7.1 Code: `openplc_reaction_time_test.py`

→ **[scripts/openplc_reaction_time_test.py](../scripts/openplc_reaction_time_test.py)**

### 7.2 Walkthrough

**Configuration:**
- `PLC_IP = "127.0.0.1"` assumes OpenPLC Runtime is running on the same Pi as this script. I ended up using the actual Pi IP instead — get it with `hostname -I`.
- `THRESHOLD_C` / `SCALE` must match the `Threshold` constant in the ST program exactly (30.00°C × 100 = 3000).
- `HYSTERESIS` — how far below the threshold temperature needs to drop before the script re-arms. Prevents one shaky reading right at the boundary from generating a bunch of false triggers. Waiting about 10 seconds after triggering usually lets the sensor cool enough to re-arm.

**Main loop:**
1. Read temperature, scale and clamp to valid unsigned 16-bit range (0–65535) for the Modbus register.
2. Only send a Modbus write if the scaled value actually changed — reduces unnecessary network traffic when temperature is stable.
3. Prints a self-overwriting status line (`\r` + `end=""`) so the terminal doesn't scroll on every iteration.
4. **Crossing detection:** if `armed` and temp is above threshold, capture `t0` right before the write, then tight-poll `read_coils` in a loop (no sleep) waiting for `%QX0.0` to go `True`.
5. **Re-arm:** once temperature drops back below `THRESHOLD_C - HYSTERESIS`, `armed` goes back to `True`.

**Known limitation:** The inner polling loop has no timeout — if the PLC never reacts, the script will hang there. During testing I ran `pt100_test.py` in a second terminal at the same time to confirm the sensor wasn't failing in the background.

---

## 8. Issue Log

### Issue #1 — Sensor reads 0 Ω / -242°C after starting the OpenPLC program

> This is also in [Known Issues](../issues/KNOWN_ISSUES.md) since it's the most important bug I found.

**Symptom:** PT100 readings are correct right up until I click "Start PLC" in the runtime. The instant the PLC starts, the sensor reports 0 Ω and ~-242°C. Stopping the PLC doesn't fix it — only unplugging and repowering the Pi restores correct readings.

**Diagnosis:**

I checked pin states with `pinctrl` for GPIO 5, 7, 8, 9, 10, 11 — once with the PLC stopped, once right after starting it:

| Pin    | Role        | Before Start PLC | After Start PLC |
|--------|-------------|-----------------|-----------------|
| GPIO5  | MAX31865 CS | output, HIGH    | **input**, HIGH |
| GPIO7  | SPI0 CE1    | output, HIGH (idle) | output, **LOW** |
| GPIO8  | SPI0 CE0    | output, HIGH (idle) | output, **LOW** |
| GPIO9  | SPI0 MISO   | SPI function, LOW | **input**, LOW |
| GPIO10 | SPI0 MOSI   | SPI function, HIGH | **input**, HIGH |
| GPIO11 | SPI0 SCLK   | SPI function, LOW | **input**, HIGH |

Every pin changes function the moment "Start PLC" is pressed.

**Root cause:** Setting the hardware layer to "Raspberry Pi" hardcodes a set of GPIO pins as digital inputs/outputs the instant the PLC starts — completely independent of what the ST program actually does. Those pins included GPIO 5, 9, 10, 11 (reassigned to inputs) and GPIO 7, 8 (reassigned to outputs). This tears down the SPI bus entirely. Only a full power cycle resets the GPIO function registers.

**Fix:** This project only needs Modbus registers for data exchange — it never actually needs OpenPLC to control real Pi GPIO pins. So:

1. OpenPLC Web UI → **Settings → Hardware**
2. Change from **Raspberry Pi** to **Blank for Linux**

   > Make sure you pick the *Linux* variant specifically. The generic "Blank" option tries to compile for Windows and will break things differently.

3. Restart the runtime.

**Status:** ✅ Fixed — sensor no longer breaks on PLC start.

---

## 9. Current Status

- [x] PT100 + MAX31865 wiring confirmed working
- [x] OpenPLC Modbus server enabled, ST program deployed
- [x] Latency test script working end-to-end
- [x] GPIO/SPI conflict bug (Issue #1) found, root-caused, and fixed
- [ ] Re-collect latency measurements post-fix (multiple trials needed)

---

## 10. Changelog

**2026-06-29**
- Diagnosed and fixed Issue #1 (GPIO/SPI conflict from OpenPLC's Raspberry Pi hardware layer) using `pinctrl` before/after comparison.
- Switched OpenPLC hardware layer to "Blank for Linux."
- Updated latency test script: write-on-change, reduced loop delay to 1ms polling, switched pymodbus keyword to `device_id` to match pymodbus 3.13.
