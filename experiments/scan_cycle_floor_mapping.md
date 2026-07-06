# Experiment: Scan Cycle Floor Mapping

## What This Is and Why It Matters

So far I've been running OpenPLC with a 1ms scan cycle, which seemed like a good starting point. But I haven't actually tested what happens below 1ms — every time I've tried, the program either won't compile or behaves unpredictably. I don't know if that's a hard floor, a configuration issue, or something fixable.

This experiment maps out the full scan cycle range, starting at 50ms and working down to as low as the runtime will go, recording response time at each setting. The goal is to find:

1. The lowest scan cycle time a pi 4 can run stably
2. How response time scales as cycle time decreases
3. Where things start to break (won't compile, crashes, misses cycles)

This feeds directly into the jitter characterization experiment (`scan_cycle_jitter_characterization.md`), **run this one first**.

---

## Setup

### What's needed

- Raspberry Pi 4 running OpenPLC Runtime v3
- OpenPLC Editor on your computer
- The existing button + LED circuit from the response time test (same wiring, same ladder logic program)
- SSH access from a second machine

### Why SSH from a second machine is required

Running the test script and the OpenPLC runtime on the same Pi causes a conflict where the runtime's hardware layer claims the GPIO pins at startup, which kills the test script's access. SSHing in from a second machine lets the test script run externally while the runtime stays untouched on the Pi. The Pi runs the PLC; your computer runs the measurement script over SSH.

---

## How to Change the Scan Cycle Time

In the OpenPLC Editor:

1. Open your existing ladder logic project
2. Go to **Resources** in the left panel → double-click **resource0**
3. Find the **Task** configuration — there's a field called **Cyclic Task**
4. Set it to the value you want to test (in milliseconds, e.g. `T#1ms`)
5. Do a **Clean Build** and re-upload the `.st` file to the runtime
6. Restart the PLC from the Dashboard

---

## Test Procedure

Run through each cycle time in the table below. For each one:

1. Set the cycle time, rebuild, upload, restart PLC
2. SSH into the Pi from your computer
3. Activate your venv: `source my-env/bin/activate`
4. Run the test script: `python3 ~/scan_cycle_floor_test.py --cycle-ms X --samples 500`
5. Record the results in the table

### Cycle times to test

| Cycle time | Status | Mean (ms) | Std dev (ms) | Min (ms) | Max (ms) | Notes |
|------------|--------|-----------|--------------|----------|----------|-------|
| 50 ms | | | | | | |
| 20 ms | | | | | | |
| 10 ms | | | | | | |
| 5 ms  | | | | | | |
| 2 ms  | | | | | | |
| 1 ms  | | | | | | |
| 0.5 ms | | | | | | |
| 0.25 ms | | | | | | |
| 0.1 ms | | | | | | |

**Signs of instability to watch for:**
- Response time suddenly jumps way up even though cycle time went down
- Very high std dev (>50% of mean) — means the PLC is missing scan cycles
- Runtime crashes or restarts mid-test
- The script reports timeouts on button presses

---

## Script

**→ [scripts/scan_cycle_floor_test.py](../scripts/scan_cycle_floor_test.py)**

Usage:
```
python3 scan_cycle_floor_test.py --cycle-ms 1 --samples 500
```

- `--cycle-ms` : the scan cycle time you set in OpenPLC (used to label the output file)
- `--samples`  : number of button presses to record (500 is good, 1000 for more confidence)

Output: `scan_floor_results_Xms_TIMESTAMP.csv`

---

## What to Look For in the Results

**Healthy behavior:** As cycle time decreases, mean response time should decrease roughly proportionally and std dev should stay low relative to mean.

**Signs you've hit the floor:** Mean response time stops decreasing even as you lower the cycle time further. This means the Pi can't actually execute a full scan in the time you're asking — it's falling behind.

**Signs of instability:** Std dev spikes relative to mean. A std dev that's more than ~30% of the mean suggests the scheduler is occasionally preempting the PLC process, causing missed cycles. This is an OS-level limitation of running on a non-real-time kernel

---

## Results

**Lowest stable cycle time found:**

**Response time at lowest stable setting:**

**Where it broke:**

**Takeaway:**

