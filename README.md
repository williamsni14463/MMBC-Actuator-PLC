# MMBC Actuator PLC — Raspberry Pi OpenPLC Research Repo

This is my working documentation for an ongoing research project where I'm turning a Raspberry Pi into a software PLC using OpenPLC, then using it to test actuator response times and sensor integration.

This repo is a living document with setup guides, experiment logs, issues I ran into, and results. It's meant to be readable for someone starting from scratch with this hardware/software stack.

---

## What's in here

```
MMBC-Actuator-PLC/
│
├── setup/                        # Step-by-step setup guides (do these first)
│   
├── experiments/                  # My R&D logs for each experiment
│
├── scripts/                      # Python scripts used in experiments
│
├── issues/                       # Known issues & fixes in one place
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

## Known Issues

All issues/bugs are collected in [issues/KNOWN_ISSUES.md](issues/KNOWN_ISSUES.md).

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

> The goal is eventually to use a Pi-based PLC to control an actuator & sensors in a real system, these experiments are building toward that.
