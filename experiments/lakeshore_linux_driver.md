# Native Linux Driver for the Lake Shore 240

## Overview

This project implements a native Linux driver for the Lake Shore 240 Temperature Controller using [PyUSB](https://github.com/pyusb/pyusb).

Unlike the official Lake Shore software, this implementation does not require proprietary Windows drivers or the USBXpress runtime. Communication is performed directly over USB by reproducing the exact initialization sequence executed by the official Windows software.

This work was completed as part of the **MAMBA** controls development effort.

---

## Motivation

The MAMBA control system requires temperature data from a Lake Shore 240 to be integrated directly into a Raspberry Pi PLC (Industrial Shields RPIPLC) running Linux.

The official Lake Shore software only supports Windows and does not expose a Linux-compatible API suitable for embedded control. Therefore, a native USB driver was required so temperature data could be read directly by the Pi and used to drive PLC logic.

---

## Problem

Initial attempts failed despite the device being successfully detected on USB.

The Raspberry Pi could locate the device:

```
VID: 0x1FB9
PID: 0x0205
```

However, none of the standard SCPI queries returned data:

- `*IDN?` returned nothing
- `KRDG? 1` returned nothing
- `SRDG? 1` returned nothing

USB communication appeared functional at the transport level (the device enumerated, endpoints were found, transfers didn't error), but the device never entered its command-response mode.

---

## Investigation Process

### Attempt 1 — Generic USBXpress initialization

The first implementation attempted to initialize the device using commonly documented USBXpress control transfers. The initialization included:

- interface enable
- endpoint reset
- endpoint flush
- alternate configuration attempts
- multiple line-termination combinations (`\r\n`, `\n`, `\r`)
- timeout protection on every USB call
- endpoint stall recovery

This prevented the Pi from hanging on a stalled endpoint, but the Lake Shore never replied to any query.

### Attempt 2 — Hardened USB communication

A more defensive USB implementation (`usbx2.py`) was written to make debugging safe to iterate on. Features included:

- a timeout on every single USB call (nothing could block more than ~1 s)
- `usb_reset()` before the handshake, to clear stalled state left by a prior crashed run
- safe wrappers around every control/bulk transfer so a stall prints a message and continues instead of freezing the process
- endpoint draining before each query
- multiple candidate command terminators tried automatically
- a hard overall time budget with guaranteed clean exit

This confirmed the Pi could talk to the USB interface safely — no more frozen desktop sessions — but still produced no valid SCPI responses. This ruled out "the code is hanging" as the problem and isolated it to "the handshake is wrong."

### Root Cause Analysis

Rather than continuing to guess at additional control transfers, USB traffic from the official Windows driver was captured using **USBPcap** while the Windows software talked to the same device. Comparing that capture against the Linux implementation revealed two incorrect assumptions:

**1. Incorrect request recipient**

The original implementation sent control transfers using:

```
bmRequestType = 0x40   (targets the USB device)
```

The Windows driver instead used:

```
bmRequestType = 0x41   (targets the USB interface)
```

Sending requests to the wrong recipient meant the device's USBXpress interface never actually received the commands meant to configure it, even though the transfers completed without a USB-level error.

**2. Missing USB configuration steps**

The Windows driver also performed several vendor-specific configuration transfers that had been omitted entirely from earlier attempts:

- interface enable
- interface configuration
- line configuration
- modem/handshake configuration
- baud rate set (115200)
- TX buffer purge
- RX buffer purge

Once these were replayed **exactly**, in the same order, with the same payloads captured from the Windows driver, communication succeeded immediately.

---

## Final Initialization Sequence

The following vendor-specific control requests are replayed exactly as captured from the Windows driver (all with `bmRequestType = 0x41`):

| Step | bRequest | wValue | Purpose |
|------|----------|--------|---------|
| 1 | `0x00` | `0x0001` | Enable interface |
| 2 | `0x03` | `0x0800` | Configuration |
| 3 | `0x13` | `0x0000` | Line configuration (payload: `00000000000000000080000000200000`) |
| 4 | `0x19` | `0x0000` | Handshake / modem configuration (payload: `000000001113`) |
| 5 | `0x1e` | `0x0000` | Set baud rate = 115200 (payload: `00c20100`) |
| 6 | `0x07` | `0x0200` | Purge transmit buffer |
| 7 | `0x07` | `0x0100` | Purge receive buffer |

After this sequence completes, the protocol is plain ASCII SCPI over the bulk endpoints:

```
*IDN?
KRDG? 1     (Kelvin reading, channel 1)
SRDG? 1     (Sensor/resistance reading, channel 1)
```

Commands are terminated with `\n` on write; responses are terminated with `\r\n` on read. Responses come back over the bulk **IN** endpoint (typically `0x81`), with commands sent on the bulk **OUT** endpoint (typically `0x01`).

---

## Driver Architecture

```
Lake Shore 240
      │
      │  USB
      ▼
   PyUSB
      │
USBXpress Initialization
 (captured control-transfer sequence)
      │
  Bulk Endpoints
      │
  ASCII SCPI Commands
      │
LakeShore240 Python Class
      │
   Applications
```

---

## Dependencies

- Python 3
- [PyUSB](https://github.com/pyusb/pyusb) (`python3-usb`)
- `libusb-1.0`

Install on Debian/Raspberry Pi OS:

```bash
sudo apt install -y python3-usb libusb-1.0-0
```

### Optional udev rule (avoids needing `sudo` to run)

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1fb9", ATTR{idProduct}=="0205", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-lakeshore240.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Unplug and replug the device after adding the rule.

> **Note:** if a run ends badly (e.g. `pipe error` / endpoint stall), always unplug/replug the 240 before the next attempt — a stalled endpoint needs a device power-cycle to clear, not just a script restart.

---

## Driver API (`ls240_driver.py`)

```python
from ls240_driver import LakeShore240

ls = LakeShore240()

ls.idn()            # -> identification string, e.g. "LSCI,MODEL240..."
ls.kelvin(channel)   # -> float, temperature in Kelvin (or None)
ls.ohms(channel)     # -> float, sensor resistance in Ohms (or None)
ls.query(command)    # -> raw string response to any SCPI command
ls.close()           # release the USB interface cleanly
```

`channel` defaults to `1` on `kelvin()` / `ohms()`.

---

## Example Programs

### Temperature Polling (`temp_poll.py`)

```bash
python3 temp_poll.py
```

Continuously polls channel 1 every 10 seconds and prints:

- timestamp
- temperature in Kelvin
- temperature in Celsius
- sensor resistance in Ohms

### PLC Threshold Demonstration (`temp_coil.py`)

```bash
sudo python3 temp_coil.py
```

This is the end-to-end proof-of-concept: **real cryogenic sensor input → software threshold logic → physical PLC output.**

Pipeline:

```
Lake Shore 240
      ↓
Python Driver (ls240_driver.py)
      ↓
Temperature Threshold Logic (with hysteresis)
      ↓
Digital PLC Output (Q0.0)
```

Behavior:

- Digital output goes **TRUE / HIGH** when temperature rises above **30 °C**
- Digital output goes **FALSE / LOW** when temperature falls below **28 °C**
- The 2 °C gap (hysteresis) prevents the output from chattering when the reading hovers near the trip point
- On `Ctrl-C`, the output is forced **LOW** before exit, so the system never left in an energized state after the script stops

This maps directly onto standard PLC/ladder-logic conventions: the same behavior would be built in ladder as a coil driven by two comparators (one for the trip point, one for the reset point), so the Python proof-of-concept is a 1:1 stand-in for the eventual OpenPLC ladder/ST implementation.

---

## PLC Integration Notes

After native temperature acquisition was working, `temp_coil.py` was developed to integrate the driver with the Industrial Shields Raspberry Pi PLC hardware.

The application:

1. Uses `LakeShore240` from `ls240_driver.py` to continuously read temperature.
2. Implements configurable threshold logic with hysteresis (30 °C trip / 28 °C reset).
3. Drives a physical PLC digital output (`Q0.0`, configurable) **HIGH** when the threshold is exceeded and **LOW** when temperature falls below the reset point.
4. Forces the output **LOW** on shutdown to guarantee a safe state.

### Installing the Industrial Shields PLC library

```bash
git clone https://github.com/Industrial-Shields/librpiplc
cd librpiplc
cmake -B build -DPLC_VERSION=RPIPLC_V6 -DPLC_MODEL=RPIPLC_57AAR
cmake --build build/ -- -j$(nproc)
sudo cmake --install build/
sudo ldconfig
cd ..

git clone https://github.com/Industrial-Shields/python3-librpiplc
cd python3-librpiplc
sudo pip3 install . --break-system-packages
cd ..
```

> Confirm `PLC_VERSION` (V4 vs V6) and `PLC_MODEL` match the physical board label before building — an incorrect version/model will cause the pin mapping to be wrong.

Verify the install:

```bash
python3 -c "import librpiplc; print('librpiplc OK')"
```

---

## Result

This completed the first end-to-end software pipeline for the bench test:

```
Lake Shore 240
      ↓
Native USB Driver
      ↓
Temperature Reading
      ↓
Threshold Logic (with hysteresis)
      ↓
Industrial Shields PLC Digital Output
```

This validates that the Raspberry Pi can simultaneously acquire cryogenic sensor data over USB and generate deterministic PLC digital outputs, forming the foundation for further MAMBA automation tasks (e.g. triggering an AKD2G motion-task actuation instead of a coil, or folding this logic into a combined `mamba_bench.py` alongside pressure and vacuum readings).

---

