# Experiment: OpenPLC Button → LED Response Time Test

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
