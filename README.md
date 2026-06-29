# MMBC Actuator PLC — Raspberry Pi + OpenPLC Research Repo

This is my working documentation for an ongoing research project where I'm turning a Raspberry Pi into a software PLC using OpenPLC, then using it to test actuator response times and sensor integration.

This repo is a living document with setup guides, experiment logs, issues I ran into, and results. It's meant to be readable for someone starting from scratch with this hardware/software stack.

---

## 📁 What's in here

```
MMBC-Actuator-PLC/
│
├── setup/                        # Step-by-step setup guides (do these first)
│   ├── 1-raspberry-pi-ssh-setup.md
│   ├── 2-openplc-runtime-setup.md
│   └── 3-example-raspberry-pi-plc.md
│
├── experiments/                  # My R&D logs for each experiment
│   ├── pt100_openplc_progress_log.md
│   └── openplc-response-time-test.md
│
├── scripts/                      # Python scripts used in experiments
│   ├── plc_response_test.py
|   ├──openplc_reaction_time_test.py
│   └── pt100_test.py
├── issues/                       # Known issues & fixes in one place
│   └── KNOWN_ISSUES.md
│
└── README.md                     
```

---

## Where to start

If you're new to this setup, work through the **setup/** folder in order:

1. [Raspberry Pi SSH Setup](setup/1-raspberry-pi-ssh-setup.md) — flash the OS, connect to the Fermilab network, SSH in
2. [OpenPLC Runtime Setup](setup/2-openplc-runtime-setup.md) — install and start the OpenPLC runtime on the Pi
3. [Example PLC Program](setup/3-example-raspberry-pi-plc.md) — build and run a simple button → LED program as a sanity check

Once setup is done, the **experiments/** folder has some R&D work I've been doing.

---

## Experiments

### [Response Time Test — Button → LED](experiments/openplc-response-time-test.md)
Measures how fast the PLC reacts to a button press and turns on an LED. Uses a Python script to physically monitor the LED output line and time 50 presses. Found that the scan cycle time (originally 20ms) was the bottleneck — reduced to under 1ms.

### [PT100 + Modbus Latency Test](experiments/RND_pt100_openplc_progress_log.md)
Measures end-to-end latency from a PT100 temperature sensor crossing a threshold → OpenPLC detecting it via Modbus → Python confirming the output bit changed. R
---

## Known Issues

The big stuff is documented in the experiment logs, but the highlights are collected in [issues/KNOWN_ISSUES.md](issues/KNOWN_ISSUES.md).

---

## Hardware used
- Raspberry Pi 4
- Adafruit MAX31865 RTD amplifier
- PT100 RTD (4-wire)
- Breadboard, jumper wires, 220Ω & 10kΩ resistors, pushbutton, LED

## Software
- Raspberry Pi OS Bookworm 64-bit
- OpenPLC Runtime v3
- OpenPLC Editor 
- Python 3 (`adafruit-blinka`, `adafruit-circuitpython-max31865`, `pymodbus`, `RPi.GPIO`)

---

> Questions or context on the project: this is part of ongoing work at MMBC/Fermilab. The goal is eventually to use a Pi-based PLC to control actuators in a real system — these experiments are building toward that.
