# OpenPLC Response Time Test

This test measures how quickly the PLC reads a button press and reacts by turning on the LED

**Everything from the '3-example-raspberry-pi-plc' tutorial carries over:**
- Wiring is identical (button on Pin 11 / GPIO17, LED on Pin 16 / GPIO23)
- The OpenPLC ladder logic program does not need to be changed
- The OpenPLC Runtime must be running with the PLC started in the browser dashboard

---

## 1. Add One Wire

Run a jumper from the **GPIO23 side** of the 220Ω resistor to **Pin 18 / GPIO24**.

This gives Python a tap into the LED output line. The PLC and LED should be unaffected.

```
Pin 16 (GPIO23) ──┬──── 330Ω ──── LED (+) ──── GND
                  │
             Pin 18 (GPIO24)   
```

> Make sure the jumper is between the resistor and the GPIO 23 plug in, if its on the otherside the voltage drop will be zero

---

## 2. Install Dependency

In the Raspberry Pi terminal, install the python GPIO library

```bash
sudo apt install python3-rpi.gpio
```

---

## 3. Add the Python Script

From your computer, ssh into the pi and create a new file called plc_response_test.py

```bash
nano ~/plc_response_test.py
```

Paste the contents of `plc_response_test.py` from this repository into the file then save with Ctrl+X → Y → Enter.

---

## 4. Run the Test

Make sure the OpenPLC Runtime is running and the PLC is started in the browser dashboard, then run:

```bash
sudo python3 ~/plc_response_test.py
```

in either a new ssh terminal on your computer, or manually type it into the pi terminal.

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

**Info**
- Press and fully release between each prompt
- Press briefly
- Wait for the LED to turn off before the next press
- If a press times out, the script skips it and asks you to try again

---
## 5. Issue Log

**Problem:**
Initial measurements of the button press response time in the PLC system showed inconsistent and unusually low-latency readings clustered between 0–20 ms, with high variance and no meaningful resolution between events. This made it impossible to accurately characterize the true system response time.

**Root Cause:**
The issue was traced to the OpenPLC scan/cycle time configuration, which was set to approximately 20 ms per cycle. Because the PLC logic only updates once per scan cycle, all input → output timing measurements were effectively quantized to the cycle interval, causing artificial clustering and uncertainty in the recorded response times.

**Fix:**
The PLC cycle time can be adjusted. However, the cycle timing resolution cannot exceed the scan period. More testing needs to be done to find the absolute minimum cycling time without breaking the program. So far, I have contained it under 1ms, but I am hopeful I can find ways for the system to run faster.

## 6. Results

After the button has been pressed all 50 times, a summary will be printed out.

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

Results are also saved to `plc_latency_results.csv` in the same directory.
---

