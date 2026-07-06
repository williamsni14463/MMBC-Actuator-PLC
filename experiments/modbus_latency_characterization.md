# Experiment: Modbus Latency Characterization

---

## 1. What This Is and Why It Matters

Measures the raw latency of the full Modbus round trip in a tight automated loop across thousands of samples.

The signal path being measured:

```
Python writes register (%QW0 = 1)
    -> OpenPLC scan cycle picks it up
        -> PLC logic sets coil (%QX0.0 = TRUE)
            -> Python reads coil back over Modbus
```

This measures: **Modbus write -> PLC scan -> Modbus read.** Nothing else.

### Why thousands of samples matter

The PT100 latency test gave 28 trials and already revealed something important; most results clustered around 0.45–1.1ms, but trial 25 spiked to 3.643ms. That spike is the OS scheduler preempting the PLC process mid-cycle. With 28 samples you can see it happened, but you can't say how often. With 2000+ samples you can characterize the spike rate precisely. Put simply, is it 1 in 28? 1 in 200? 1 in 1000? That frequency is what determines whether the Pi is reliable enough for a given application at such a low cycle time.

### What the results tell you

**Floor (min / 10th percentile):** Fixed overhead from two Modbus TCP transactions plus Python processing. This is irreducible with this software stack regardless of how low you push the scan cycle time. Estimated from the PT100 data to be around ~0.45ms.

**Typical range:** From the floor up to floor + cycle_time. This is normal quantization, the trigger lands at a random point in the 1ms scan window. 

**Spikes above cycle_time:** Samples where the PLC took longer than one full cycle to respond (cycle time is 1ms). These are OS scheduler preemption events (jitter). The percentage of samples that fall here is the jitter rate.

---

## 2. How This Differs from Previous Experiments

The key improvements over the past tests: 
1. No sensor in the loop (cleaner signal path) fully automated (no human timing variance)
2. Enough samples to characterize the tail of the distribution.
3. Fully automated with no human timing variance as seen in the plunge test and button test

---

## 3. OpenPLC Program

The ST program is intentionally as simple as possible to reduce load on CPU. It just mirrors the register state to the coil. Any latency measured is communication + scan overhead, not logic.

```
VAR
    TriggerReg : INT AT %QW0;
    OutputBit  : BOOL AT %QX0.0;
END_VAR

IF TriggerReg > 0 THEN
    OutputBit := TRUE;
ELSE
    OutputBit := FALSE;
END_IF;
```

### Modbus map

| OpenPLC location | Modbus type | Address | Written by | Read by |
|-----------------|-------------|---------|------------|---------|
| `%QW0` | Holding register | 0 | Python (writes 1 to trigger, 0 to reset) | PLC program |
| `%QX0.0` | Coil | 0 | PLC program | Python |

### Deployment

1. OpenPLC Editor → New Project → Structured Text
2. Paste the VAR block and IF statement above
3. Set cycle time to the value you want to test (e.g. `T#1ms`)
4. **Clean Build** and upload
5. Runtime web UI → Settings → Modbus Server → Enable (port 502)
6. Dashboard → Start PLC

---

## 4. Setup

No new hardware needed beyond what's already in place for the PT100 experiment. The OpenPLC runtime just needs to be running with the program above uploaded and the Modbus server enabled.

If running the script from a second machine over the network (recommended), set `--plc-ip` to the Pi's IP address from `hostname -I`.

If running locally on the Pi, `127.0.0.1` (default) works fine, but make sure the OpenPLC hardware layer is set to **Blank for Linux** since this experiment uses no GPIO, and "Raspberry Pi" hardware layer will fight for pins unnecessarily.

**Dependencies:**
```
pip install pymodbus
```

---

## 5. Running the Test

### Basic run (1ms cycle, 2000 samples)

```
python3 modbus_latency_characterization.py --cycle-ms 1 --samples 2000
```

### Run across multiple cycle times

Run this once per cycle time, changing the setting in OpenPLC Editor between each run. Suggested progression (start high, work down):

```
python3 modbus_latency_characterization.py --cycle-ms 10   --samples 2000
python3 modbus_latency_characterization.py --cycle-ms 5    --samples 2000
python3 modbus_latency_characterization.py --cycle-ms 2    --samples 2000
python3 modbus_latency_characterization.py --cycle-ms 1    --samples 2000
python3 modbus_latency_characterization.py --cycle-ms 0.5  --samples 2000
```

Stop if the runtime won't compile or produces >10% timeouts — that's the floor.

### Progress output

The script prints a running update every 200 samples:

```
  [  200/2000]  mean=0.814ms  std=0.203ms  max=2.891ms  spikes>1ms: 6
  [  400/2000]  mean=0.809ms  std=0.198ms  max=3.102ms  spikes>1ms: 11
  ...
```

`spikes>1ms` is the running count of OS jitter events — samples where the PLC took longer than one full cycle to respond.

---

## 6. Understanding the Output

```
  Floor estimate (10th pct) :   0.4821 ms
  Min                       :   0.4483 ms
  Mean                      :   0.8047 ms
  Median                    :   0.8121 ms
  Std dev                   :   0.2014 ms
  Max                       :   4.1230 ms
  95th percentile           :   1.0891 ms
  99th percentile           :   1.2340 ms
  99.9th percentile         :   3.8910 ms
  ──────────────────────────────────────────────────────────────
  OS jitter events (>1ms)   :   47  (2.35% of samples)
  Timeouts                  :    0
```

**Floor (expected @.48ms):** Fixed Modbus + Python overhead. This won't decrease no matter how low you set the cycle time — it's the cost of two TCP transactions plus Python. Consistent with the ~0.45ms floor seen in the PT100 data.

**Mean (expected @0.80ms):** Average of floor + random position in the 1ms scan window. Expected to be roughly floor + cycle_time/2.

**Max:** The worst OS preemption event in 2000 samples.

---

## 7. Results Table

| Cycle time | Samples | Floor (ms) | Mean (ms) | Std dev (ms) | 99th pct (ms) | Max (ms) | Jitter rate | Notes |
|------------|---------|------------|-----------|--------------|---------------|----------|-------------|-------|
| 10 ms | | | | | | | | |
| 5 ms  | | | | | | | | |
| 2 ms  | | | | | | | | |
| 1 ms  | | | | | | | | |
| 0.5 ms | | | | | | | | |

**What to look for across cycle times:**
- Floor should stay roughly constant, it's a property of the software stack, not the cycle time
- Mean should decrease as cycle time decreases (floor + cycle_time/2)
- Jitter rate is the critical number, does it get worse at lower cycle times? That tells you where the Pi starts struggling to keep up

---
