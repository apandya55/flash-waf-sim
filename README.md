# FlashWAF — Python NAND Flash Translation Layer Simulator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23655212.svg)](https://doi.org/10.5281/zenodo.23655212)
[![GitHub Release](https://img.shields.io/badge/release-v1.0.0-blue.svg)](https://github.com/apandya55/flash-waf-sim/releases/tag/v1.0.0)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Test Suite](https://img.shields.io/badge/tests-36%20passed-brightgreen.svg)](tests/)

FlashWAF is an open-source Python simulator that models page-mapped Flash Translation Layer (FTL) page allocation, out-of-place writes, greedy garbage collection, and page-program write amplification under controlled synthetic workloads. It provides a clean, dependency-light research software platform for inspecting FTL dynamics, but it does not simulate physical NAND analog timing, multi-channel parallelism, ECC, or production SSD controller firmware.

---

## Key Features

| Component / Module | Implemented Behavior | Explicit Exclusions |
|:---|:---|:---|
| **`FlashSimulator`** (`flash_sim/simulator.py`) | In-memory page-level L2P mapping table, sequential free-page allocation, greedy garbage collection with erase-count tie-breaking, block erasures, runtime invariant assertions. | Multi-plane commands, channel interleaving, wear-leveling pools, non-volatile mapping persistence. |
| **`Block` & `Page`** (`flash_sim/models.py`) | Explicit tri-state page lifecycle (`FREE` &rarr; `VALID` &rarr; `INVALID`), block-level invalid counters, per-block erase tracking. | Sub-page programming, bit-level errors, charge leakage, physical threshold voltages. |
| **`WorkloadGenerator`** (`flash_sim/workload.py`) | Deterministic synthetic workloads: uniform random, parameterized disjoint hot/cold (e.g. 80/10, 90/5), and discrete Zipfian distributions using common random numbers. | Production trace replay (e.g. Blktrace/SPC-1), asynchronous queue depths, host file systems. |
| **`RingBuffer`** (`flash_sim/buffer.py`) | In-memory circular staging buffer with batch flushing to the flash device. | Incomplete L2P indexing semantics; educational staging model only. |
| **`PowerLossSimulator`** (`flash_sim/power_loss.py`) | Volatile buffer loss accounting and uncommitted payload reporting during injected crash events. | Crash recovery replay, supercapacitor hold-up timing, journal reconstruction. |

---

## How It Works: FTL, Garbage Collection, and Write Amplification

NAND flash memory exhibits an inherent physical constraint known as the **erase-before-write** property: while read and program (write) operations occur at the granularity of individual **pages** (e.g., 4 KiB), data can only be erased at the granularity of an entire **block** (e.g., 32 or 64 pages).

Because an already-programmed page cannot be directly overwritten in-place, modern solid-state storage employs a **Flash Translation Layer (FTL)**:

1. **Out-of-Place Updates**: When the host issues a write to an existing Logical Block Address (LBA), the FTL writes the updated data to an open `FREE` physical page, updates its internal Logical-to-Physical (`L2P`) map, and marks the previous physical page as `INVALID`.
2. **Space Exhaustion & Thresholds**: As host writes continue, the supply of free pages drops below a configured threshold (`gc_threshold_free_pages`), triggering background or on-demand **Garbage Collection (GC)**.
3. **Greedy Garbage Collection**: FlashWAF selects a "victim block" containing the maximum count of `INVALID` pages (breaking ties by picking the block with the fewest erasures). Any remaining `VALID` pages in that victim block must be copied to newly allocated free pages before the entire victim block can be erased.
4. **Write Amplification Factor (WAF)**: The extra internal page programming required to preserve live data during block reclamation causes the physical write volume to exceed host write volume:

$$\text{WAF} = \frac{\text{Host Page Writes} + \text{GC Relocation Page Writes}}{\text{Host Page Writes}} = \frac{H + G}{H}$$

In FlashWAF, this metric is measured precisely by tracking physical write counters across distinct simulation phases.

---

## Quick Start

### Installation

Requires Python 3.9 or newer (tested on Python 3.12).

```sh
# Clone repository
git clone https://github.com/apandya55/flash-waf-sim.git
cd flash-waf-sim

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package and test dependencies
pip install -e '.[dev]'
```

### Running the Simulator in Python

```python
import random
from flash_sim import FlashSimulator

# Initialize a flash device: 16 erase blocks, 32 pages per block (512 physical pages)
sim = FlashSimulator(num_blocks=16, pages_per_block=32)

# Write full-page logical payloads
sim.write_logical_page(lba=10, data=b"Record payload A" * 256)
assert sim.read_logical_page(lba=10).startswith(b"Record payload A")

# Apply synthetic random overwrites across 350 active LBAs (approx 70% physical occupancy)
rng = random.Random(42)
for _ in range(2000):
    lba = rng.randint(0, 349)
    sim.write_logical_page(lba=lba, data=b"Updated payload" * 256)

# Verify page-state invariants across all blocks and L2P mappings
sim.check_invariants()

# Inspect internal page program metrics
host_writes = sim.physical_page_writes
gc_copies = sim.gc_page_copies
waf = (host_writes + gc_copies) / host_writes

print(f"Host Writes: {host_writes}")
print(f"GC Page Copies: {gc_copies}")
print(f"Block Erasures: {sim.block_erasures}")
print(f"Write Amplification Factor (WAF): {waf:.3f}")
```

---

## Reproducible Research Experiments

FlashWAF includes deterministic, reproducible benchmark pipelines evaluated across multiple occupancy rates, workload distributions, and geometry configurations.

### Primary Occupancy and Locality Experiment

The primary experiment initializes the simulator by prepopulating all active logical addresses, executes 5,000 warm-up updates to establish steady-state page residency, and records metrics over the subsequent 5,000 measured updates. Thirty paired pseudorandom seed blocks cover six conditions (40%, 70%, and 85% mapped occupancy under uniform vs. 80/10 hot/cold traffic), totaling 180 runs.

To reproduce the primary experiment:

```sh
python experiments/research_sensitivity.py
python experiments/summarize_results.py
```

#### Verified Numerical Results

| Physical Occupancy | Active LBAs | Uniform Mean WAF | Hot/Cold (80/10) Mean WAF | Paired Contrast ($\Delta$ WAF) | 95% Descriptive Paired Student-$t$ CI ($df=29$) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **40%** | 205 | 1.0000 | 1.3299 | **+0.32987** | [0.32665, 0.33310] |
| **70%** | 358 | 1.4886 | 2.0952 | **+0.60656** | [0.60054, 0.61258] |
| **85%** | 435 | 2.5020 | 3.3066 | **+0.80465** | [0.78676, 0.82253] |

*Difference-in-differences relative to 40% occupancy: +0.27669 at 70% (CI: [0.27049, 0.28289]) and +0.47477 at 85% (CI: [0.45711, 0.49244]).*

> **Scientific Boundary**: These measurements characterize this specific Python simulator under synthetic workload construction. They do not predict real-world SSD endurance, vendor-specific controller behavior, or universal physical NAND properties.

### Robustness & Sensitivity Grid

To inspect sensitivity to warm-up duration, flash geometry, and workload skew at 70% occupancy:

```sh
python experiments/robustness_validation.py
python experiments/summarize_robustness.py
python experiments/analytical_reference.py
```

- **Warm-up lengths** (0; 2,500; 5,000; 10,000 updates): Hot/cold minus uniform contrast remains consistently positive (+0.504 to +0.605).
- **Larger geometry** (32 blocks $\times$ 32 pages = 1,024 physical pages): Paired contrast is +0.574 ($df=9$).
- **Skew sensitivity**: More concentrated traffic increases the contrast: +0.601 for 80/10, +0.780 for Zipf ($\alpha=1.2$), and +1.004 for 90/5.

Raw JSON trial outputs are archived in `research/results/` and figures in `research/figures/`.

---

## Repository Architecture

```text
flash-waf-sim/
├── flash_sim/                 # Core simulation package
│   ├── __init__.py            # Public package exports
│   ├── simulator.py           # FlashSimulator FTL engine & greedy GC
│   ├── models.py              # Block, Page, and PageState definitions
│   ├── workload.py            # Uniform, Hot/Cold, and Zipf workload generators
│   ├── buffer.py              # RingBuffer circular staging model
│   └── power_loss.py          # PowerLossSimulator volatile accounting
├── experiments/               # Reproducible experiment drivers
│   ├── research_sensitivity.py    # Primary 30-seed 180-run pipeline
│   ├── summarize_results.py       # Primary statistical summary & figure generator
│   ├── robustness_validation.py   # 10-seed sensitivity grid driver
│   ├── summarize_robustness.py    # Sensitivity summary & figure generator
│   └── analytical_reference.py    # Closed-form theoretical comparison
├── research/                  # Scientific documentation and data artifacts
│   ├── METHODOLOGY.md         # Simulation protocol, invariants, and boundaries
│   ├── VALIDATION.md          # Statistical checks and verification history
│   ├── AUDIT.md               # Historical audit & retirement of early exploratory claims
│   ├── results/               # Deterministic raw trial outputs (.json)
│   └── figures/               # High-resolution vector and raster plots
├── docs/                      # Technical documentation and static project site
│   ├── site/                  # Crawlable static project site (HTML/JSON-LD/Scholar)
│   └── write-amplification-in-page-mapped-ftl.md # In-depth technical explainer
├── tests/                     # Comprehensive test suite (36 tests)
│   ├── test_simulator.py      # FTL operations, GC triggers, and invariant assertions
│   ├── test_models.py         # Block and page lifecycle transitions
│   ├── test_workload.py       # Workload generation distributions and determinism
│   └── test_buffer.py         # Buffer and power loss models
├── paper/                     # LaTeX manuscript and compiled PDF report
│   ├── main.tex               # Technical report source
│   ├── references.bib         # Academic bibliography
│   └── main.pdf               # Compiled 6-page research report
├── CITATION.cff               # Machine-readable Citation File Format
├── .zenodo.json               # Zenodo archive metadata
└── pyproject.toml             # Project packaging and dependency definitions
```

---

## Testing & Verification

Run the complete test suite (36 tests):

```sh
pytest -v
```

Tests verify:
- Out-of-place write allocation and L2P table updates.
- Invalidation counters when mapped LBAs are rewritten.
- Greedy victim block selection and live valid-page copy integrity during garbage collection.
- Flash state invariant checks (`total_pages == free + valid + invalid`).
- Seeded determinism across workload generators.

---

## Frequently Asked Questions (FAQ)

### How does FlashWAF compare to full-system SSD emulators like FEMU or MQSim?
Tools like FEMU (QEMU-based emulator) and MQSim (NVMe/PCIe simulator) are full-stack, cycle-accurate or queue-driven simulators modeling host PCIe controllers, NVMe submission/completion queues, DRAM cache controllers, and multi-channel flash chips. FlashWAF is intentionally lightweight and algorithmic: written in pure Python, it focuses specifically on the interaction between logical page mapping, out-of-place invalidation, and greedy garbage collection. It executes thousands of operations per second with zero external C++ dependencies, making it ideal for educational use, algorithm testing, and controlled computational experiments.

### Why does hot/cold temporal locality increase write amplification under greedy GC without cold-data separation?
When an FTL does not physically partition hot and cold pages into separate blocks, hot pages (frequently updated) and cold pages (rarely updated) become mixed in the same allocation blocks. When a block is reclaimed by greedy GC, cold pages that have remained valid must be copied to a new block, consuming free pages and triggering further GC rounds. Without dedicated cold-data identification or dual-pool separation, high update skew accelerates block turnover and increases the volume of copied live data compared to uniform access at equal mapped occupancy.

### How is write amplification factor (WAF) calculated?
FlashWAF defines WAF at the logical-to-physical page programming interface:

$$\text{WAF} = \frac{\text{Host Page Writes} + \text{GC Relocation Page Writes}}{\text{Host Page Writes}}$$

This isolates algorithmic amplification caused by garbage collection from operating system filesystem metadata, controller journal writes, or sub-page write buffering.

### Can FlashWAF replay block traces or custom I/O patterns?
Yes. The core method `sim.write_logical_page(lba, data)` accepts arbitrary integer logical addresses. Users can iterate through parsed trace files (e.g. SNIA or FIU block traces) and stream requests into the simulator.

### Does FlashWAF predict physical SSD lifetime or endurance?
No. FlashWAF does not model cell oxide wear breakdown, floating-gate/charge-trap physics, read disturbance, temperature drift, bad-block retirement, or vendor-proprietary wear-leveling algorithms. It characterizes logical page movement in this specific Python simulation model.

---

## Citation & Archival

If you use FlashWAF in academic research, educational coursework, or benchmarking studies, please cite the versioned Zenodo release:

### BibTeX

```bibtex
@software{pandya2026flashwaf,
  author       = {Pandya, Arnav},
  title        = {{FlashWAF: a page-mapped flash simulator}},
  month        = oct,
  year         = 2026,
  publisher    = {Zenodo},
  version      = {v1.0.0},
  doi          = {10.5281/zenodo.23655212},
  url          = {https://doi.org/10.5281/zenodo.23655212}
}
```

### APA Style

> Pandya, A. (2026). *FlashWAF: a page-mapped flash simulator* (Version 1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23655212

The companion technical report is available in [`paper/main.pdf`](paper/main.pdf).

---

## Limitations & AI-Assisted Disclosure

- **Hardware Modeling Exclusions**: FlashWAF does not simulate physical latency (read/program/erase microseconds), multichannel interleaving, dynamic wear leveling pools, crash recovery journals, or ECC.
- **Buffer & Durability Models**: The included `RingBuffer` and `PowerLossSimulator` are educational demonstrations with simplified LBA mapping semantics; they are not integrated into the primary FTL write amplification benchmarks.
- **AI-Assisted Development**: Generative AI tools assisted in test suite generation, codebase refactoring, and drafting documentation. All simulation models, invariant constraints, experimental executions, and numerical analyses were independently developed, validated, and verified by the author.

---

## License

FlashWAF is released under the [MIT License](LICENSE).
Copyright &copy; 2026 Arnav Pandya.
