# Experiment: MAX31865 Conversion Time Verification & PT100 Thermal Response

---

## 1. How the RDY Pin Works

DRDY (labeled **RDY** on the Adafruit breakout) goes LOW when a new conversion result is available in the data register. When a read operation of the RTD resistance data register occurs, DRDY returns HIGH.

So the cycle in continuous mode looks like:

```
chip finishes conversion
    -> RDY goes LOW
        -> Python detects LOW, reads register
            -> RDY goes HIGH
                -> chip starts next conversion
                    -> [~20ms later] RDY goes LOW again
```

---

## 2. Wiring
```
Adafruit breakout "RDY" pin  ->  GPIO25 (Pi Pin 22)
```

Look at your MAX31865 breakout header. The pins in order are typically:
`VIN  GND  CLK  SDO  SDI  CS  RDY`

The RDY pin is the last one in that row. Connect it to GPIO25 (Pi Pin 22) with a jumper wire.

### Full pin table

| Pi Pin | GPIO | Role |
|--------|------|------|
| 1      | 3V3  | MAX31865 VIN |
| 6      | GND  | MAX31865 GND |
| 19     | GPIO10 (MOSI) | MAX31865 SDI |
| 21     | GPIO9  (MISO) | MAX31865 SDO |
| 23     | GPIO11 (SCLK) | MAX31865 CLK |
| 29     | GPIO5  | MAX31865 CS |
| 22     | GPIO25 | **RDY pin** |
| 37     | GPIO26 | Trigger (water closes circuit to GND) |

---

## 4. Software

Two scripts, run in order:

| Script | Does |
|--------|------|
| [`scripts/verify_conversion_time.py`](../scripts/verify_conversion_time.py) | Counts 100 RDY pulses and measures the interval. Saves verified mean to `verified_conversion_time_ms.txt`. |
| [`scripts/sensor_thermal_response_drdy.py`](../scripts/sensor_thermal_response_drdy.py) | Runs the plunge test. Reads `verified_conversion_time_ms.txt` automatically if it exists. |

**Dependencies**
```
pip install adafruit-blinka adafruit-circuitpython-max31865
sudo apt install python3-rpi.gpio
```

---

## Part 1

Have the sensor sitting in air or room-temperature water, connected as normal.

```
sudo python3 verify_conversion_time.py
```

The script measures 100 RDY pulse intervals and prints each one live:

```
  Pulse    Interval (ms)    Interval (us)
  ------  --------------  --------------
       1          20.312           20312
       2          20.287           20287
       3          20.319           20319
  ...
```

Then a summary:

```
  Results  (100 intervals)
  Min    :    20.244 ms   (   20244 us)
  Mean   :    20.301 ms   (   20301 us)
  Median :    20.298 ms   (   20298 us)
  Max    :    20.381 ms   (   20381 us)
  Std dev:     0.021 ms   (      21 us)

  Datasheet expected : ~20.5 ms
  Measured mean      :  20.301 ms
  Difference         :  1.0%
```

The suymmary tells us 2 things,
1. Whether the chip is actually running at the expected rate of ~20ms conversion
2. The exact floor, any thermal response time shorter than this mean is not resolvable by this sensor

The mean is saved to `verified_conversion_time_ms.txt` and the thermal response script reads it automatically.

---

## Part 2

```
sudo python3 sensor_thermal_response_drdy.py
```

### Baseline

Keep the sensor in its starting medium and let it collect 30 fresh readings. Watch the std dev — under 0.1°C is good:

```
  Baseline : 23.441 C  (std dev = 0.0241 C)
```

### The plunge

When the script says "Waiting for trigger":
1. Hold the sensor above (not in) the hot water 
2. Lower the sensor in one smooth motion along with connecting the jumper from GPIO 37 to GND
3. Hold still once submerged

The trigger fires the moment the circuit completes. You'll see:
```
  Trigger fired at 11:42:03.847 — logging started!
```

### Analysis

```
  Baseline            : 23.4410 C
  Final (last 10 avg) : 52.8730 C
  Step size           : +29.4320 C
  Conversion floor    : 20.30 ms  [measured (verified_conversion_time_ms.txt)]

  Onset  (>0.5 C change)
    214.20 ms  (214200 us)

  Tau    (63.2% of step)
    1840.70 ms  (1840700 us)

  90%    settling
    4230.10 ms  (4230100 us)

  95%    settling
    5910.40 ms  (5910400 us)
```

The conversion floor is printed next to the results so you always know your resolution limit. Onset is meaningful as long as it's well above the floor (several conversion cycles, not just 1-2). If onset is within 2 conversion cycles of t0, the script flags it — that means the "onset" you're seeing might just be the first conversion that happened to catch the new temperature, not a real dead-time measurement.

---
