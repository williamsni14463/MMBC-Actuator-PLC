# Experiment: Scan Cycle Jitter Characterization

## What This Is and Why It Matters

Getting a fast mean response time isn't enough to call a Pi a viable PLC. Industrial PLCs are trusted in real systems because they're *predictable* — if a PLC says it has a 1ms scan cycle, it hits 1ms every single time, not on average. The worst-case matters just as much as the mean.

This is the difference between a Pi that *looks* fast and a Pi that's actually reliable enough to control something. If mean latency is 0.8ms but worst-case is 15ms, a control loop tuned for 0.8ms will occasionally blow up. That's not acceptable in an industrial setting.

This experiment takes the scan cycle settings identified in the floor mapping experiment (`scan_cycle_floor_mapping.md`) and characterizes the full distribution of response times at each stable setting — not just mean and std dev, but the 95th, 99th, and 99.9th percentile worst cases. The goal is to answer: **how predictable is the Pi's response time, and how does predictability change as scan cycle time decreases?**

Run the floor mapping experiment first — this one uses those results to decide which cycle times to test.

---

## Why Jitter Happens on a Pi

The Raspberry Pi runs a standard Linux OS, which uses a general-purpose scheduler. That scheduler doesn't know or care that OpenPLC needs to run every 1ms — it'll happily preempt the PLC process to handle a network packet, a USB event, a background system task, or anything else. When that happens, the PLC misses its scan window and response time spikes.

Industrial PLCs run on dedicated hardware or real-time OSes that guarantee the scan cycle runs on time, every time. This is the Pi's main structural weakness as a PLC candidate. This experiment measures how bad that weakness actually is in practice.

A future experiment (RT kernel patch) will test whether installing a `PREEMPT_RT` real-time kernel on the Pi reduces jitter — but first we need this baseline to compare against.

---

## Setup

Same as the floor mapping experiment — SSH from a second machine, existing button + LED circuit, OpenPLC runtime running on the Pi.

See [scan_cycle_floor_mapping.md](scan_cycle_floor_mapping.md) for the full setup walkthrough.

---

## Test Procedure

Pick the 3–4 most interesting scan cycle times from the floor mapping results:
- The lowest stable setting found
- 1ms (reference point from previous experiments)
- One or two settings in between

For each cycle time, collect **2000+ samples** — more than the floor mapping test, because we're looking at tail behavior (99th percentile) which needs more data to be statistically meaningful.

Run:
```
python3 scan_cycle_jitter_test.py --cycle-ms X --samples 2000
```

### Results table

| Cycle time | Mean (ms) | Std dev (ms) | 95th pct (ms) | 99th pct (ms) | 99.9th pct (ms) | Max (ms) | Jitter ratio |
|------------|-----------|--------------|---------------|---------------|-----------------|----------|--------------|
| 1 ms | | | | | | | |
| 0.5 ms | | | | | | | |
| [floor] | | | | | | | |

**Jitter ratio** = std dev / mean. Lower is more predictable. Industrial PLCs typically achieve jitter ratios below 0.05 (5%). If the Pi is hitting 0.3+ it's a meaningful weakness to document.

---

## Script

**→ [scripts/scan_cycle_jitter_test.py](../scripts/scan_cycle_jitter_test.py)**

Usage:
```
python3 scan_cycle_jitter_test.py --cycle-ms 1 --samples 2000
```

Output:
- `jitter_results_Xms_TIMESTAMP.csv` — raw sample data
- `jitter_summary_Xms_TIMESTAMP.txt` — summary stats including percentiles

The script runs fully automatically — no button pressing, it drives the GPIO pin in a tight loop so you can collect thousands of samples quickly without being there for each one.

---

## What a Good Result Looks Like

If the Pi is performing well as a PLC at a given cycle time, you'd expect to see:

- Std dev under ~20% of mean
- 99th percentile under ~3× mean
- No extreme outliers (>10× mean) in 2000 samples

If you're seeing 99th percentile at 5–10× the mean, that's the OS scheduler causing missed scan cycles — the Pi hit that setting's mean on most cycles but occasionally got preempted badly. Worth noting in the log as a structural limitation and flagging as something the RT kernel experiment is designed to address.

---

## How This Compares to Industrial PLCs

Some reference points from datasheets for context when writing up results:

| PLC | Typical scan cycle | Jitter |
|-----|-------------------|--------|
| Allen-Bradley Micro820 | 0.2 – 2ms | <1% (dedicated HW) |
| Siemens S7-1200 | 1ms typical | <1% (dedicated HW) |
| Raspberry Pi 4 (this experiment) | ? | ? |

The Pi will almost certainly not match dedicated hardware on jitter. The question is whether the gap is small enough to be acceptable for the use cases this project is targeting — low-cost, non-safety-critical automation — which is a different bar than a factory floor controller.

---

## Issue Log

*(append issues here as they come up)*

---

## Results

*(fill in after running)*

**Jitter at 1ms cycle:**

**Jitter at lowest stable cycle:**

**Worst single outlier observed:**

**Takeaway:**

---

## Changelog

**2026-07-06**
- Experiment designed as follow-on to scan_cycle_floor_mapping.md
- Requires floor mapping to be run first to identify which cycle times to test
- Automated GPIO loop approach chosen over manual button press to enable 2000+ sample collection
- Added jitter ratio metric and industrial PLC comparison table for context
