# Write Amplification in a Simplified Page-Mapped NAND Flash Translation Layer

**Author:** Arnav Pandya  
**Project:** [FlashWAF](https://github.com/apandya55/flash-waf-sim) (Version 1.0.0)  
**Permanent Identifier (DOI):** [10.5281/zenodo.23655212](https://doi.org/10.5281/zenodo.23655212)

---

## 1. Introduction: The Asymmetry of NAND Flash Memory

Solid-state storage built on NAND flash memory operates under an intrinsic physical constraint: **erase-before-write**. In NAND flash:
- **Read** operations occur at the granularity of a **page** (typically 4 KiB to 16 KiB).
- **Program** (write) operations also occur at page granularity, but a page can only be programmed if it is currently in an erased state.
- **Erase** operations can only be performed at the granularity of an **erase block**, which aggregates multiple pages (typically 32 to 512 pages per block).

Because a host operating system frequently issues overwrites to existing logical sector addresses (LBAs), a storage device cannot physically overwrite flash cells in place without first erasing the entire containing block. Erasing an entire block on every sector overwrite would introduce catastrophic write latency and destroy device endurance within hours.

To solve this, solid-state drives (SSDs) and flash controllers implement a specialized firmware layer: the **Flash Translation Layer (FTL)**.

---

## 2. Page-Mapped FTL Architecture and Out-of-Place Updates

FlashWAF models a pure **page-mapped FTL**. In a page-mapped architecture, any host Logical Block Address (LBA) can reside in any physical page on any block in the flash array.

### Page State Lifecycle

Each physical page in FlashWAF exists in one of three discrete states (defined in `flash_sim/models.py` as `PageState`):

```text
       [ FREE ] ──(Host Write / GC Copy)──> [ VALID ]
          ▲                                    │
          │                                (Host Overwrite to same LBA)
          │                                    ▼
       (Block Erase) <───────────────────── [ INVALID ]
```

1. **`FREE`**: The page has been erased and contains no data. It is ready to be programmed.
2. **`VALID`**: The page contains current, live data associated with an active logical address in the Logical-to-Physical (`L2P`) translation table.
3. **`INVALID`**: The page contains historical, obsolete data. The host issued an overwrite to the same LBA, and the FTL allocated a new free page elsewhere for the update.

### Out-of-Place Write Mechanics in FlashWAF

When `FlashSimulator.write_logical_page(lba, data)` is invoked (implemented in `flash_sim/simulator.py`):
1. The FTL checks if `lba` is already present in `self.l2p`.
2. If mapped, the old physical location `(old_block, old_page)` is marked `PageState.INVALID`, decrementing that block's valid count and incrementing its invalid count.
3. A free page `(new_block, new_page)` is allocated sequentially from the active write block.
4. The page state is transitioned to `PageState.VALID`, its payload is stored, and `self.l2p[lba]` is updated.
5. `self.physical_page_writes` is incremented.

This decoupling allows fast sequential writes without synchronous block erasures, but it steadily accumulates invalid pages across the storage pool.

---

## 3. Greedy Garbage Collection and Write Amplification

As the host continues writing, the total count of free pages across all blocks drops. When `total_free_pages <= gc_threshold_free_pages`, the simulator invokes **Garbage Collection (GC)** (`FlashSimulator.garbage_collect()` in `flash_sim/simulator.py`).

### Greedy Victim Selection

FlashWAF implements a classic **greedy** reclamation policy (Bux & Iliadis, 2010):
- The FTL scans all candidate blocks containing invalid pages (excluding the active write block).
- It selects the **victim block** that maximizes `invalid_page_count`.
- If multiple candidate blocks have an identical number of invalid pages, the simulator breaks ties by choosing the block with the lowest historical `erase_count` (a basic wear-leveling heuristic).

### The Relocation Cost

Let $B$ denote the number of pages per block. If a victim block contains $V$ valid pages and $I = B - V$ invalid pages:
1. To reclaim the block, the $V$ valid pages must be preserved. The FTL allocates $V$ free pages in another block and programs the valid data there, updating the `L2P` map for each relocated page. Each relocation increments `self.gc_page_copies`.
2. The victim block is erased (`victim.erase()`), transitioning all $B$ pages back to `FREE` and incrementing `self.block_erasures`.
3. The net gain in free pages is:
   $$\Delta \text{Free} = B - V = I$$

If $V > 0$, internal programming work was expended purely to reclaim space.

### Formal Metric: Write Amplification Factor (WAF)

The **Write Amplification Factor (WAF)** is defined as the ratio of total physical page programming operations executed by the flash device to user-requested logical page programming operations:

$$\text{WAF} = \frac{\text{Host Page Writes} + \text{GC Relocation Page Writes}}{\text{Host Page Writes}} = \frac{H + G}{H} = 1 + \frac{G}{H}$$

In an ideal system where blocks only ever contain invalid pages ($V = 0$ for all victims), $G = 0$ and $\text{WAF} = 1.0$. In practical workloads, $V > 0$, yielding $\text{WAF} > 1.0$.

---

## 4. The Influence of Storage Occupancy and Over-Provisioning

Let $N$ denote the total number of physical pages across all blocks ($N = \text{num\_blocks} \times \text{pages\_per\_block}$), and let $M$ denote the number of distinct active logical addresses mapped by the host ($M \le N$).

The **mapped occupancy ratio** is:
$$\rho = \frac{M}{N}$$

The unmapped fraction $1 - \rho = \frac{N - M}{N}$ represents physical **over-provisioning (OP)** space available to the garbage collector.

### Theoretical Baseline Under Uniform Random Writes

Under long-running uniform random write traffic, invalid pages distribute uniformly across blocks. When the system reaches steady state, every block selected for garbage collection contains approximately the average proportion of valid pages:
$$V_{\text{avg}} \approx \rho \cdot B$$

Reclaiming a block yields $I \approx (1 - \rho) B$ free pages at the expense of copying $V \approx \rho B$ valid pages. The theoretical steady-state write amplification for uniform random traffic under greedy GC is bounded by (Agarwal & Marrow, 2010; Desnoyers, 2014):

$$\text{WAF}_{\text{uniform}} \approx \frac{1}{1 - \rho}$$

- At **40% occupancy** ($\rho = 0.40$), $\text{WAF}_{\text{theory}} \approx \frac{1}{1 - 0.40} = 1.67$ (if all blocks are subject to GC; in prepopulated finite experiments with high free space, WAF remains near 1.0 until free blocks deplete).
- At **70% occupancy** ($\rho = 0.70$), $\text{WAF}_{\text{theory}} \approx \frac{1}{1 - 0.70} = 3.33$.
- At **85% occupancy** ($\rho = 0.85$), $\text{WAF}_{\text{theory}} \approx \frac{1}{1 - 0.85} = 6.67$.

As occupancy approaches 100% ($\rho \to 1.0$), available over-provisioning vanishes, and write amplification escalates asymptotically.

---

## 5. Workload Locality and Cold-Data Contamination

A central question in flash storage research is how **temporal locality** affects write amplification.

### The Dynamics in a Non-Partitioned Page-Mapped FTL

In real storage workloads, write traffic is rarely uniform. Workloads typically follow skewed distributions where a small fraction of "hot" LBAs receive the vast majority of write requests, while "cold" LBAs are updated infrequently.

In FlashWAF's default architecture:
- Both hot and cold pages are written into the same single active block.
- Hot pages are overwritten frequently, quickly turning invalid in older blocks.
- Cold pages, once written, remain `VALID` for extended periods.

Because hot and cold data share the same physical blocks:
1. When greedy GC selects a victim block that has accumulated many invalid hot pages, that block almost always contains several persistent valid **cold pages**.
2. Those cold pages must be copied into the active allocation block, mingling them again with newly incoming hot pages.
3. The presence of cold pages in every block prevents blocks from ever becoming 100% invalid, forcing continuous valid-page relocation.

### Empirical Evidence from FlashWAF

In FlashWAF's primary 30-seed paired experiment (prepopulated active LBAs, 5,000 warm-up updates, 5,000 measured updates; `experiments/research_sensitivity.py`):

```text
Primary Contrast: Hot/Cold (80/10) vs. Uniform
---------------------------------------------------------------------------------
Occupancy   Active LBAs   Uniform WAF   Hot/Cold WAF   Difference (Δ WAF)   95% CI
---------------------------------------------------------------------------------
  40%           205         1.0000        1.3299          +0.32987       [0.327, 0.333]
  70%           358         1.4886        2.0952          +0.60656       [0.601, 0.613]
  85%           435         2.5020        3.3066          +0.80465       [0.787, 0.823]
---------------------------------------------------------------------------------
```

Across all three occupancy levels, hot/cold traffic produced higher write amplification than uniform traffic ($\Delta \text{WAF} > 0$), and this gap widened as mapped occupancy increased (+0.33 at 40% vs. +0.80 at 85%).

### Why Modern Enterprise FTLs Differ

Production SSD controllers avoid this penalty by implementing **hot/cold data separation** (e.g. dual-pool allocation, multi-stream write frontiers, or clustering policies; Chen et al., 2019; Wang et al., 2015). When cold pages are isolated into dedicated "cold blocks," those blocks rarely experience writes and are never selected as GC victims, while "hot blocks" rapidly become completely invalid ($V \approx 0$), dropping GC copy overhead toward zero.

FlashWAF demonstrates the direct consequence of omitting hot/cold separation in a simplified FTL.

---

## 6. Mathematical Invariants and Simulator Validation

To guarantee computational consistency, FlashWAF enforces structural invariants at each simulation boundary (`sim.check_invariants()`):

1. **Conservation of Physical Pages**:
   $$\sum_{b \in \text{Blocks}} (\text{free}_b + \text{valid}_b + \text{invalid}_b) = \text{num\_blocks} \times \text{pages\_per\_block}$$

2. **L2P Mapping Bijectivity**:
   Every entry in `l2p[lba] = (b, p)` must reference a page with `state == PageState.VALID` and `page.lba == lba`.

3. **Active Page Count**:
   The count of valid pages across the entire device must equal the number of unique active logical addresses currently mapped in `l2p`.

These invariants are tested across 36 automated unit and integration tests in `tests/test_simulator.py`.

---

## 7. Model Boundaries and Real-World Hardware Exclusions

FlashWAF is an algorithmic and educational model designed for reproducible research. To interpret its outputs responsibly, researchers must note the specific physical phenomena it **excludes**:

| Physical Phenomenon | Real Hardware SSD Behavior | FlashWAF Simulation Model |
|:---|:---|:---|
| **Write Granularity** | Program per page; erase per block. | Program per page; erase per block (**Modeled**). |
| **GC Policy** | Cost-benefit, FIFO, or windowed greedy. | Pure greedy with erase-count tie-breaking (**Modeled**). |
| **NAND Latency** | Asymmetric microseconds ($t_{\text{R}} \approx 25\mu\text{s}, t_{\text{PROG}} \approx 500\mu\text{s}, t_{\text{BERS}} \approx 3\text{ms}$). | Untimed logical step counter (**Excluded**). |
| **Interleaving** | Multi-channel, multi-plane, multi-die parallelism. | Single monolithic block array (**Excluded**). |
| **Wear Leveling** | Dynamic and static cold-block swapping pools. | Greedy erase-count tie-breaker only (**Excluded**). |
| **Data Separation** | Multi-stream, cold data pooling. | Single shared allocation frontier (**Excluded**). |
| **Reliability / ECC** | Bit errors, voltage shifts, read disturbance, bad blocks. | Error-free memory array (**Excluded**). |
| **Host Interface** | NVMe / PCIe submission and completion queues. | Synchronous Python API calls (**Excluded**). |

---

## 8. Reproducing the Simulation

To reproduce the primary experiment and sensitivity checks locally:

```sh
# Clone and prepare environment
git clone https://github.com/apandya55/flash-waf-sim.git
cd flash-waf-sim
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# Run automated tests
pytest -v

# Execute primary 30-seed experiment (180 condition runs)
python experiments/research_sensitivity.py
python experiments/summarize_results.py

# Execute 10-seed sensitivity grid and analytical validation
python experiments/robustness_validation.py
python experiments/summarize_robustness.py
python experiments/analytical_reference.py
```

All raw outputs are saved as deterministic JSON files in `research/results/` and figures in `research/figures/`.

---

## 9. References

1. **Agarwal, S., & Marrow, M.** (2010). Closed-form expressions for worst-case and average write amplification in NAND flash. *IEEE Systems and Information Engineering Design Symposium (SIEDS)*.
2. **Agrawal, N., Prabhakaran, V., Wobber, T., Davis, J. D., Manasse, M., & Panigrahy, R.** (2008). Design tradeoffs for SSD performance. *USENIX Annual Technical Conference (ATC)*.
3. **Bityutskiy, A.** (2005). JFFS3 design issues: Garbage collection. *White paper, University of Cambridge*.
4. **Bux, W., & Iliadis, I.** (2010). Performance of greedy garbage collection in flash-based solid-state drives. *Performance Evaluation*, 67(11), 1172–1186.
5. **Chen, Y., et al.** (2019). HCFTL: A hot/cold separated page-level flash translation layer. *IEEE Transactions on Very Large Scale Integration (VLSI) Systems*.
6. **Desnoyers, P.** (2014). Analytic modeling of SSD write performance. *ACM Transactions on Storage (TOS)*, 10(2), 1–25.
7. **Hu, X.-Y., Eleftheriou, E., Haas, R., Iliadis, I., & Pletka, R.** (2009). Write amplification analysis in flash-based solid state drives. *ACM International Conference on Computing Frontiers (CF)*, 191–200.
8. **Peleato, B., Agarwal, S., Cioffi, J. M., Chou, M., & Qin, X.** (2012). Towards minimizing write amplification in SSDs via valid page distribution modeling. *IEEE Transactions on Communications*, 60(11), 3237–3248.
9. **Van Houdt, B.** (2013). A mean field model for a class of garbage collection algorithms in flash-based solid state drives. *ACM SIGMETRICS*, 41(1), 191–202.
10. **Wang, C., et al.** (2015). A data-centric flash translation layer with cold data identification. *IEEE Transactions on Consumer Electronics*.
