# FlashWAF v1.0.0 — Initial Release

This is the initial release of **FlashWAF**, an open-source discrete-event simulator for NAND flash memory, the Flash Translation Layer (FTL), and Write Amplification Factor (WAF) dynamics.

I built this project to explore a classic storage systems problem: flash cells can only write in small pages (4 KiB) but must erase in large blocks (256 KiB). When an application writes small records directly to flash, the drive spends more time moving stale data around during garbage collection than writing real data. FlashWAF gives you an instrumented sandbox to measure that wear and test how user-space buffering changes the equation.

---

## What’s in this release

* **Core FTL Simulator (`flash_sim`):**
  * Three-state page lifecycle (`FREE`, `VALID`, `INVALID`) tracking individual flash cells.
  * Logical-to-Physical (L2P) address translation with out-of-place writes.
  * Greedy Garbage Collection with wear-leveling tie-breaking (prefers blocks with the lowest erase counts).
  * Hardware telemetry: tracks physical page writes, GC page migrations, and block erase wear cycles.

* **Volatile Ring Buffer:**
  * User-space circular buffer aggregating 128-byte updates into 4 KiB page flushes.
  * Multi-page chunking to support arbitrary buffer capacities (4 KiB to 16 KiB).

* **Durability & Crash Simulator:**
  * Sudden power-loss fault injection across configurable flush policies.
  * Tracks committed vs. uncommitted byte loss and measures the durability vs. wear Pareto frontier.

* **Experimental Harness & Artifacts:**
  * Reproducible WAF benchmark suite (unbuffered vs. buffered).
  * Multi-seed robustness validation grid across access locality skews and working set sizes.
  * Analytical figures and per-block silicon wear heatmaps.
  * Complete LaTeX research manuscript draft in `paper/`.

---

## Benchmark Highlights

Across a 3.2 MB workload (25,000 updates of 128 bytes across 3,200 addresses on a 16 MiB flash chip):

* **Direct unbuffered writes:** WAF spiked to **66.2×** with **747 block erasures** and 26,713 wasted GC page copies. Over half of all drive I/O was internal housekeeping.
* **4 KiB ring buffer:** WAF dropped to **1.0×** and block erasures dropped to **0**.
* **Durability trade-off:** Under 50 random power cuts, the 4 KiB buffer preserved **97.1%** of data while keeping maximum data loss bounded below 4 KiB per crash event.

---

## Getting Started

```bash
git clone https://github.com/apandya55/flash-waf-sim.git
cd flash-waf-sim
pip install -e '.[dev]'
pytest
```

Run the WAF comparison benchmark:
```bash
python3 experiments/benchmark_waf.py
```

Generate the full visualization suite:
```bash
python3 experiments/generate_figures.py
```

---

## A Note on Scope

FlashWAF is an algorithmic and architectural model designed for experiments and education. It models the core invariants of a page-mapped FTL under synthetic workloads, but it doesn't try to replicate controller firmware quirks, read disturb, or hardware capacitor discharge curves. All raw data and reproduction scripts are included in the repo.
