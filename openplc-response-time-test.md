# OpenPLC Response Time Test (Raspberry Pi)

This test measures how quickly the PLC reads a button press and reacts by turning on the LED — i.e. input → output latency.

**Everything from the previous tutorial carries over:**
- Wiring is identical (button on Pin 11 / GPIO17, LED on Pin 16 / GPIO23)
- The OpenPLC ladder logic program does not need to be changed
- The OpenPLC Runtime must be running with the PLC started in the browser dashboard

---

## 1. Add One Wire

Run a jumper from the **GPIO23 side** of the 330Ω resistor to **Pin 18 / GPIO24**.

This gives Python a passive monitor tap on the LED output line. The PLC and LED are unaffected.

```
Pin 16 (GPIO23) ──┬──── 330Ω ──── LED (+) ──── GND
                  │
             Pin 18 (GPIO24)   ← new jumper goes here
```

> Make sure the jumper is on the GPIO23 side of the resistor, not the LED side. The wrong side will read 0V.

---

## 2. Install Dependency

On the Raspberry Pi, install the GPIO library if not already present:

```bash
sudo apt install python3-rpi.gpio
```

---

## 3. Add the Python Script

On your **computer**, open a terminal and copy the script to the Pi:

```bash
scp plc_response_test.py pi@YOUR_PI_IP:/home/pi/
```

Or create it directly on the Pi over SSH:

```bash
nano ~/plc_response_test.py
```

Paste the contents of `plc_response_test.py`, then save with Ctrl+X → Y → Enter.

---

## 4. Run the Test

Make sure the OpenPLC Runtime is running and the PLC is started in the browser dashboard, then run:

```bash
sudo python3 ~/plc_response_test.py
```

The script will prompt you to press the button one at a time:

```
====================================================
  OpenPLC Response Time Test
  2026-06-15 11:15:00
====================================================
  Button  : GPIO17  (Pin 11)
  Monitor : GPIO24  (Pin 18)
  Samples : 50
  Output  : plc_latency_results.csv
────────────────────────────────────────────────────
  Press the button 50 times when prompted.
  Wait for the LED to turn off between each press.

[  1/ 50]  Press the button...    18.423 ms
[  2/ 50]  Press the button...    17.891 ms
...
```

**Tips:**
- Press and fully release between each prompt
- Press briefly rather than holding down
- Wait for the LED to turn off before the next press
- If a press times out, the script skips it and asks you to try again

---

## 5. Results

After all samples are collected, a summary is printed:

```
====================================================
  Results  (50 samples)
────────────────────────────────────────────────────
  Min      :   15.112 ms
  Max      :   23.447 ms
  Mean     :   18.204 ms
  Median   :   18.011 ms
  Std dev  :    1.893 ms
  95th pct :   21.330 ms
====================================================
```

Results are also saved to `plc_latency_results.csv` in the same directory. Copy it back to your computer with:

```bash
scp pi@YOUR_PI_IP:/home/pi/plc_latency_results.csv ./
```

---

## Optional: Custom Options

```bash
# Run 100 samples and save to a custom filename
sudo python3 ~/plc_response_test.py --samples 100 --out my_results.csv

# Change the timeout per press (default 2000 ms)
sudo python3 ~/plc_response_test.py --timeout-ms 5000
```

---

## What the Numbers Mean

| Stat | What it tells you |
|------|-------------------|
| Mean | Average PLC scan cycle + response time |
| Std dev | How consistent the PLC is between scans |
| Min | Best-case response (button pressed right at start of scan) |
| Max | Worst-case response (button pressed right after scan started) |
| 95th pct | Reliable upper bound — 95% of presses respond within this |

A typical OpenPLC installation on a Raspberry Pi will read somewhere between 10–50 ms mean latency depending on the configured scan cycle time.
