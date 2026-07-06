# Experiment: Button Response Time Test

This test measures how quickly the PLC reads a button press and reacts by turning on the LED.

**Everything from the [example PLC tutorial](../setup/3-example-raspberry-pi-plc.md) carries over:**
- Wiring is identical (button on Pin 11 / GPIO17, LED on Pin 16 / GPIO23)
- The OpenPLC ladder logic program does not need to be changed
- The OpenPLC Runtime must be running with the PLC started in the browser dashboard

---

## 1. Add One Wire

Run a jumper from the **GPIO23 side** of the 220Ω resistor to **Pin 18 / GPIO24**.

This gives Python a tap into the LED output line so it can detect when the LED actually turns on. The PLC and LED should be completely unaffected.

```
Pin 16 (GPIO23) ──┬──── 220Ω ──── LED (+) ──── GND
                  │
             Pin 18 (GPIO24)
```

> Make sure the jumper is between the resistor and GPIO23 — if it's on the other side, the voltage drop will be zero and Python won't see anything.

---

## 2. Install Dependency

```
sudo apt install python3-rpi.gpio
```

---

## 3. Add the Python Script

SSH into the Pi and create the script file:

```
nano ~/plc_response_test.py
```

Paste in the contents of [`scripts/plc_response_test.py`](../scripts/plc_response_test.py) from this repo, then save with `Ctrl+X → Y → Enter`.

---

## 4. Run the Test

Make sure the runtime is running and the PLC is started, then:

```
sudo python3 ~/plc_response_test.py
```

The script will prompt you to press the button 50 times:

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

**A few tips:**
- Press and fully release between each prompt
- Press briefly — don't hold it
- Wait for the LED to turn off before the next press
- If a press times out, the script skips it and asks you to try again

---

## 5. Issue Log

### Problem: Readings were clustering at 0–20ms with high variance

Initial measurements showed all results smashed between 0–20ms with no real resolution — it was impossible to tell what was actually happening.

**Root cause:** The OpenPLC scan/cycle time was set to ~20ms per cycle. Since the PLC logic only updates once per scan, every timing measurement was quantized to that interval. That's why everything looked like a flat cluster — the system could only "see" time in 20ms chunks.

**Fix:** Reduce the PLC cycle time in the runtime settings. I got it under 1ms, which gives much better resolution. Still exploring how low it can go without causing stability issues.

---

## 6. Results

After 50 button presses, a summary prints:

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

Results are also saved to `plc_latency_results.csv` in the Pi's home directory.

**Takeaway:** With the cycle time fixed to 20ms, response times are pretty consistently in the 1–20ms range. More testing needed with different cycle time settings to characterize the floor.

---

**Further Experimenting**

This test excludes any sensors which makes the logic much simpler. Because of this, I'm going to look into how low I can get the cycle time in the PLC Editor before it breaks. That should prove what the floor is of a Pi PLC using OpenPLC.




