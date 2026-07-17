"""
make_graphs.py

Reads the Modbus latency CSV files in this folder and produces three
poster-ready PNG graphs:
    fig1_histogram.png     - latency distribution (the headline figure)
    fig2_cdf.png           - cumulative distribution (% under X ms)
    fig3_repeatability.png - box plots comparing the runs

HOW TO RUN (Windows PowerShell):
    1. Put this file in the same folder as your CSV files.
    2. cd into that folder, e.g.:  cd C:\\Users\\willi\\latency
    3. Run:  python make_graphs.py

It automatically finds every CSV starting with "modbus_latency" in the folder.

Requires: pip install numpy matplotlib
"""

import glob
import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")   # lets it save PNGs without a display
import matplotlib.pyplot as plt

# ── Find the CSV files automatically ──────────────────────────────────────────
files = sorted(glob.glob("modbus_latency*.csv"))
if not files:
    print("No files matching 'modbus_latency*.csv' found in this folder.")
    print("Make sure this script is in the same folder as your CSV files.")
    raise SystemExit(1)

print(f"Found {len(files)} file(s):")
for f in files:
    print(f"   {f}")
print()

# ── Load the latency column from each file ────────────────────────────────────
def load(fn):
    vals = []
    with open(fn, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vals.append(float(row["latency_ms"]))
    return np.array(vals)

runs = [load(f) for f in files]
pooled = np.concatenate(runs)

# ── Print the statistics ──────────────────────────────────────────────────────
def stats(d, label):
    print(f"{label:<18} N={len(d):>6}  mean={d.mean():.4f}  median={np.median(d):.4f}  "
          f"min={d.min():.4f}  max={d.max():.4f}  "
          f"p99={np.percentile(d,99):.4f}  jitter>{1.0}ms={ (d>1.0).sum()/len(d)*100:.2f}%")

print("STATISTICS")
for f, d in zip(files, runs):
    stats(d, os.path.basename(f)[:16])
stats(pooled, "POOLED")
print()

# ── Styling ───────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 19, "axes.labelsize": 16,
    "xtick.labelsize": 14, "ytick.labelsize": 14, "legend.fontsize": 13,
    "savefig.dpi": 300, "axes.linewidth": 1.2, "axes.edgecolor": "#333333",
})
FNAL_BLUE = "#0b2265"; ACCENT = "#c8102e"; GREY = "#666666"

mean = pooled.mean(); median = np.median(pooled)
p99 = np.percentile(pooled, 99)
jitter_pct = (pooled > 1.0).sum() / len(pooled) * 100

# ── FIGURE 1: histogram ───────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.5))
counts, bins, _ = ax.hist(pooled, bins=120, color=FNAL_BLUE, alpha=0.85)
ax.axvline(1.0, color=ACCENT, lw=2.2, label="1 ms scan-cycle boundary")
ax.axvline(median, color="#f0a500", lw=2.2, ls="--", label=f"Median = {median:.2f} ms")
ax.axvline(p99, color=GREY, lw=2, ls=":", label=f"99th pct = {p99:.2f} ms")
ax.set_xlabel("Round-trip latency (ms)"); ax.set_ylabel("Count")
ax.set_title(f"OpenPLC Modbus Response Latency\n"
             f"({len(pooled):,} samples, 1 ms scan cycle)", fontweight="bold", color=FNAL_BLUE)
ax.legend(frameon=True, framealpha=0.95)
ax.set_xlim(0, 1.5)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.annotate(f"OS jitter tail\n({jitter_pct:.2f}% > 1 ms)",
            xy=(1.1, counts.max()*0.10), xytext=(1.18, counts.max()*0.42),
            fontsize=12, color=ACCENT, ha="center",
            arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.5))
plt.tight_layout(); plt.savefig("fig1_histogram.png", facecolor="white"); plt.close()
print("Saved fig1_histogram.png")

# ── FIGURE 2: CDF ─────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.5))
s = np.sort(pooled); cdf = np.arange(1, len(s)+1)/len(s)*100
ax.plot(s, cdf, color=FNAL_BLUE, lw=2.5)
ax.axvline(1.0, color=ACCENT, lw=2, alpha=0.8)
for pct, lbl in [(50, "50%"), (95, "95%"), (99, "99%")]:
    v = np.percentile(pooled, pct)
    ax.plot([v, v], [0, pct], color=GREY, lw=1, ls=":")
    ax.plot([0, v], [pct, pct], color=GREY, lw=1, ls=":")
    ax.annotate(f"{lbl} < {v:.2f} ms", xy=(v, pct), xytext=(v+0.05, pct-8), fontsize=12, color="#333")
ax.set_xlabel("Round-trip latency (ms)"); ax.set_ylabel("Cumulative % of samples")
ax.set_title("Cumulative Latency Distribution", fontweight="bold", color=FNAL_BLUE)
ax.text(1.02, 15, "1 ms", color=ACCENT, fontsize=13, fontweight="bold")
ax.set_xlim(0, 1.5); ax.set_ylim(0, 100)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.grid(alpha=0.2)
plt.tight_layout(); plt.savefig("fig2_cdf.png", facecolor="white"); plt.close()
print("Saved fig2_cdf.png")

# ── FIGURE 3: repeatability box plots ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.5))
labels = [f"Run {i+1}\n({len(d)//1000}k)" if len(d) >= 1000 else f"Run {i+1}\n({len(d)})"
          for i, d in enumerate(runs)]
bp = ax.boxplot(runs, patch_artist=True, showfliers=True,
                flierprops=dict(marker="o", markersize=3, alpha=0.3,
                                markerfacecolor=GREY, markeredgecolor="none"),
                medianprops=dict(color=ACCENT, lw=2),
                boxprops=dict(facecolor=FNAL_BLUE, alpha=0.6, edgecolor=FNAL_BLUE),
                whiskerprops=dict(color=FNAL_BLUE), capprops=dict(color=FNAL_BLUE))
ax.set_xticklabels(labels)
ax.axhline(1.0, color=ACCENT, lw=1.5, ls="--", alpha=0.7, label="1 ms scan cycle")
ax.set_ylabel("Round-trip latency (ms)")
ax.set_title("Repeatability Across Runs", fontweight="bold", color=FNAL_BLUE)
ax.legend(frameon=True)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.grid(alpha=0.2, axis="y")
plt.tight_layout(); plt.savefig("fig3_repeatability.png", facecolor="white"); plt.close()
print("Saved fig3_repeatability.png")

print()
print("Done. Three PNG files are in this folder, ready for your poster.")