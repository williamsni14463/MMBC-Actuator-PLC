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

## Log
Things I want to test/learn:
1. Real-time kernel, the Raspberry Pi OS is not a real-time OS, which means the scheduler can preempt your process at any time. There's a PREEMPT_RT kernel patch for Raspberry Pi that converts it to a real-time kernel, which could dramatically reduce the jitter. Testing with and without it could be worth looking at.
2. Openplc button response time test with a new, decreased cycle time. Need to setup SSH again before I do this because if its all on the same device running the test script and the OpenPLC runtime on the same Pi means the runtime's hardware layer claims the GPIO pins at startup, which kills the test script's access. SSHing in from a second machine lets you run the test script from outside while the runtime stays untouched on the Pi.
3. Possibly switching to C++, harder/longer code but it does cycle much faster than python. I can use Claude to translate the code. I would need to see if C++ has a modbus server like Python's pymodbus.
4. Scan cycle floor mapping. So far, whenever I have tried to lower the cycle time under 1ms, the code will not compile. If we want enough data to publish, it's worth testing the cycle times from 1-50 or 100 and understand and record where it becomes unstable, misses cycles, or crashes. This is probably the most important single experiment for the "can a Pi 4 be an industrial PLC" question.
5. Jitter characterization, the mean latency alone is not enough for arguing its use as an industrial PLC. A real PLC needs consistent and predictable response times. So I want to measure standard deviation and worst-case latency across thousands of samples at each scan cycle setting. A Pi hitting 0.8ms mean but 5ms worst-case is very different from one hitting 0.8ms mean with 0.1ms std dev.
6. Might as well test the network latency baseline by measuring raw ping latency between the two machines on the local network. That gives a floor for what Modbus TCP over the network can possibly achieve, separate from PLC overhead.
7. Compare results to commercial PLC's to compare consistency.
8. It could be nothing, but industrial PLCs have dedicated hardware whereas the Pi shares the CPU load with an OS. It would be worth running a stress test in another terminal to see if response time degrades under load or refuses to work at all. This might be a big weakness of a Pi PLC.

---

> The goal is eventually to use a Pi-based PLC to control an actuator & sensors in a real system, these experiments are building toward that.
