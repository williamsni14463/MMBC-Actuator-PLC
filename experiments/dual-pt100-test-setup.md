# Setup: Two PT100 Sensors + Two MAX31865 Amplifiers on One Raspberry Pi

A simple test rig to confirm two PT100 sensors are working in the chamber. Each PT100 connects to its own MAX31865 amplifier, and both amplifiers share the Pi's SPI bus — with one important difference from the single-sensor setup: **each amplifier needs its own separate CS (chip select) pin.**

This is for reading two temperatures side by side and confirming both sensors are alive and reasonable. It's deliberately simple — no PLC, no logging, just a clear live readout.

---

## The one thing that matters most: shared SPI, separate CS

SPI is a bus — multiple devices share the same three data lines (SDI, SDO, CLK). The Pi talks to one device at a time by pulling that device's **CS (chip select)** line low. So:

- **SDI, SDO, CLK** → shared: both MAX31865 boards connect to the *same* Pi pins
- **CS** → unique: each MAX31865 gets its *own* Pi pin

If you tie both CS lines to the same pin, the Pi can't tell the boards apart and you get garbage. That's the single most common mistake with two sensors.

---

## Pinout — Sensor 1 (CS on GPIO8 / CE0)

The MAX31865 board pins are usually labeled: `VIN  GND  CLK  SDO  SDI  CS  RDY`

| MAX31865 pin | → | Pi pin (physical) | Pi signal (BCM) |
|--------------|---|-------------------|-----------------|
| VIN | → | Pin 1 | 3V3 |
| GND | → | Pin 6 | GND |
| CLK | → | Pin 23 | GPIO11 (SCLK) |
| SDO | → | Pin 21 | GPIO9  (MISO) |
| SDI | → | Pin 19 | GPIO10 (MOSI) |
| **CS** | → | **Pin 24** | **GPIO8 (CE0)** |
| RDY | → | *(not connected)* | — |

## Pinout — Sensor 2 (CS on GPIO7 / CE1)

**Everything is identical to Sensor 1 except the CS pin.** VIN, GND, CLK, SDO, SDI all go to the *same* Pi pins as Sensor 1 (you'll have two wires going into those shared points — a breadboard power rail or splice makes this tidy).

| MAX31865 pin | → | Pi pin (physical) | Pi signal (BCM) |
|--------------|---|-------------------|-----------------|
| VIN | → | Pin 1  (shared) | 3V3 |
| GND | → | Pin 6  (shared) | GND |
| CLK | → | Pin 23 (shared) | GPIO11 (SCLK) |
| SDO | → | Pin 21 (shared) | GPIO9  (MISO) |
| SDI | → | Pin 19 (shared) | GPIO10 (MOSI) |
| **CS** | → | **Pin 26** | **GPIO7 (CE1)** |
| RDY | → | *(not connected)* | — |

### Visual: the shared bus + separate CS

```
   Raspberry Pi
   ┌─────────────────────────┐
   │ Pin 1  (3V3)  ●─────────┼──┬── VIN  (Sensor 1)
   │                         │  └── VIN  (Sensor 2)
   │ Pin 6  (GND)  ●─────────┼──┬── GND  (Sensor 1)
   │                         │  └── GND  (Sensor 2)
   │ Pin 23 (CLK)  ●─────────┼──┬── CLK  (Sensor 1)
   │                         │  └── CLK  (Sensor 2)
   │ Pin 21 (MISO) ●─────────┼──┬── SDO  (Sensor 1)
   │                         │  └── SDO  (Sensor 2)
   │ Pin 19 (MOSI) ●─────────┼──┬── SDI  (Sensor 1)
   │                         │  └── SDI  (Sensor 2)
   │ Pin 24 (CE0)  ●─────────┼───── CS   (Sensor 1)   ← unique
   │ Pin 26 (CE1)  ●─────────┼───── CS   (Sensor 2)   ← unique
   └─────────────────────────┘
```

---

## Wiring each PT100 to its MAX31865

The PT100 itself connects to the *screw terminals* on the MAX31865 board (the green terminal block), not to the Pi. How you wire it depends on whether your PT100 is 2, 3, or 4 wire.

**For a 4-wire PT100** (most common for precision, and what the chamber sensors likely are):
- The MAX31865 board has 4 screw terminals for the RTD
- Connect the two wires of one pair to the outer terminals, the other pair to the inner terminals
- The Adafruit board is shipped configured for **2-wire by default** — for 3 or 4-wire you must move a jumper. Check the small solder-jumper labeled `2/3/4 WIRE` on the board and set it for your sensor. The library also needs to be told the wire count (see the script's `WIRES` setting).

**Important — reference resistor must match the sensor:**
- The Adafruit MAX31865 board comes in two versions: **PT100** (430Ω reference resistor) and **PT1000** (4300Ω reference resistor)
- For PT100 sensors, `ref_resistor = 430.0` and `rtd_nominal = 100.0`
- Using the wrong reference resistor value in the code gives wildly wrong temperatures — this is set in the script

---

## Software setup

### 1. Enable SPI on the Pi

```bash
sudo raspi-config
```
Interface Options → SPI → Enable → reboot.

Confirm the SPI devices exist after reboot:
```bash
ls /dev/spidev*
```
You should see `/dev/spidev0.0` and `/dev/spidev0.1` — these correspond to CE0 and CE1, the two CS pins we're using.

### 2. Install the libraries

On Raspberry Pi OS Bookworm, pip needs the `--break-system-packages` flag (or use a venv — see [issues/KNOWN_ISSUES.md](../issues/KNOWN_ISSUES.md) Issue #3):

```bash
pip3 install --break-system-packages adafruit-blinka
pip3 install --break-system-packages adafruit-circuitpython-max31865
```

**What these libraries do:**
- `adafruit-blinka` — provides the `board` and `digitalio` modules that let CircuitPython-style code run on a Raspberry Pi. This is what gives you `board.SPI()`, `board.D8`, etc.
- `adafruit-circuitpython-max31865` — the driver for the MAX31865 chip itself. Handles the SPI register reads and the resistance-to-temperature math.

> If `import board` fails with "No module named board," Blinka isn't set up correctly for the Pi. See the note in the earlier PT100 setup — you may need to run Adafruit's `raspi-blinka.py` setup script.

### 3. Run the test

```bash
python3 scripts/dual_pt100_test.py
```

See the script's output section below.

---

## What you'll see

```
PT100 Dual Sensor Test  —  Ctrl+C to stop

  Sensor 1 (CE0):   22.41 °C     108.71 Ω
  Sensor 2 (CE1):   22.38 °C     108.69 Ω
  Difference   :    0.03 °C
```

- Both temperatures should read close to room temperature (~20-25°C) before the chamber is cold
- The two sensors should agree within a few tenths of a degree if they're sitting near each other
- Touch one sensor with your finger and watch that channel's temperature rise — confirms it's live and you know which physical sensor is which channel
- Resistance around 108-110 Ω at room temperature is normal for a PT100 (it reads ~100 Ω at 0°C and climbs ~0.385 Ω per °C)

### Troubleshooting

**Reads ~-242°C with near-zero resistance:** classic sign of a wiring problem on that channel — usually an open connection or the RTD terminals not making contact. Check the screw terminals and the CS wiring for that specific sensor.

**Both channels read identical, suspiciously static values:** the two CS pins may be shorted together or both wired to the same Pi pin. Confirm Sensor 1's CS is on Pin 24 and Sensor 2's CS is on Pin 26.

**One channel works, the other doesn't:** the shared bus (CLK/SDO/SDI) is fine, so the problem is isolated to the broken channel — check its CS wire and its VIN/GND.

**Temperature is wildly off (hundreds of degrees):** wrong reference resistor in the code. Confirm `REF_RESISTOR = 430.0` for a PT100 board (not 4300).
