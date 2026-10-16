# FlashWAF independent audit

Audit date: 2026-10-23. Baseline environment: macOS, Python 3.12.3, pytest 9.1.1; NumPy and Matplotlib are installed. Baseline `python3 -m pytest -q`: **32 passed in 0.33 s**. `python3 experiments/benchmark_waf.py` completes in 4.23 s and reproduces its displayed 25,000 / 782 programs, 26,713 copies, 747 erasures, and 66.193 / 1.001 ratios. `python3 experiments/durability_eval.py` completes in 9.26 s. `python3 experiments/generate_figures.py` generated figures 1–3, then was interrupted after it spent over 30 s in figure 4's workload; the run did not complete. The stale `visualizations.py` imports absent `benchmark_phase3`.

## Architecture and execution path

`generate_workload` creates `(integer LBA, fixed-size bytes)` pairs using NumPy's legacy `RandomState`. The direct experiment sends every pair to `FlashSimulator.write_logical_page`; each record therefore replaces the prior page at its LBA and incurs one page program. The simulator has `Block`/`Page` objects with FREE/VALID/INVALID states, an in-memory L2P dictionary, sequential-ish free-page allocation, and greedy invalid-page-count GC with erase-count tie breaking. GC relocates valid pages before erasing its victim. Counters distinguish host-triggered page programs, GC copies, and block erasures. The buffered path queues record bytes but drops each record's LBA; it writes concatenated bytes as a page under the last pushed LBA (or an internally assigned sequential LBA). It does not implement a record index or key/value recovery mapping.

## Findings

| Severity | Finding | Evidence / consequence |
|---|---|---|
| CRITICAL | Buffered and direct benchmark semantics differ. | Direct path maintains latest value for each of 3,200 LBAs. Buffered path stores a batch under one LBA and discards the others. Equal submitted bytes do not imply equal application state; the reported 66x comparison is invalid as an application-equivalent result. |
| HIGH | README's “66x lower wear” and zero-erasure conclusions overstate the measurements. | The buffered run emits only 782 programs on 4,096 pages, below the simulator's 64-page GC reserve threshold; no sustained regime is reached. Erasures count block erase operations, not total lifetime wear or endurance. |
| HIGH | The quantity named WAF uses unlike boundaries. | Formula is programmed-page bytes (including GC copies) / submitted payload bytes. This is an application-to-modeled-device byte ratio for the direct path, but buffered path discards/repacks records. It is not a validated commercial-device WAF. |
| HIGH | Crash results are not recovery experiments. | `PowerLossSimulator` clears the volatile queue and estimates lost bytes. It has no restart, persistent record index, torn program, acknowledged-write contract, or recovery procedure. `committed_host_bytes` can be wrong when records overwrite keys or only a prefix of a buffer is lost. |
| HIGH | Simulator's correctness envelope is narrow. | It models page states and a global RAM L2P map; no metadata persistence, bad blocks, program-order constraints, latency, TRIM, wear leveling, or NAND failure. Greedy GC is simplified. No explicit geometry/input validation or public invariant checker existed at baseline. |
| MEDIUM | Baseline tests verify components, not end-to-end research semantics. | 32 tests pass, but there were no buffered-vs-direct logical-state equivalence tests, randomized invariant stress tests, or analytical accounting checks. |
| MEDIUM | Existing charts are not a reproducible paper dataset. | Plot functions contain fixed sweeps, mostly one seed, asymmetric semantics, and no raw trial files or uncertainty. Figure 4 is extremely slow due repeated full-device page scans; the full generator did not finish in the audit run. |
| MEDIUM | Wear leveling claim is overstated. | Tie-breaking by erase count during GC is not static wear leveling and does not relocate cold data; erase-count spread alone is not evidence of endurance. |
| LOW | Package metadata omits exact dependency lock/version capture. | Requirements use open lower bounds; baseline versions were not recorded by the old scripts. |

## Claims withdrawn

Withdraw the README's application-level 66x benefit, “100% wear reduction,” 4 KiB sweet spot, larger-buffer “trap,” and assertions of 97–89% data committed as durability findings. The benchmark arithmetic itself is reproducible, but its interpretation is not. Existing figures and heatmaps are exploratory illustrations, not publication evidence.

## Repairs and remaining limits

Added `FlashSimulator.check_invariants()` and targeted stress tests for latest-value preservation through GC, physical-state conservation, erase accounting, and capacity failure. These checks validate simulator bookkeeping, not NAND or crash consistency. Rather than implement a record-indexed log store and recovery protocol, the research question is narrowed to simulated page-mapped FTL sensitivity under controlled page-level overwrite workloads. The legacy buffered comparison is retained as an educational demo only and must not be interpreted as a fair policy comparison.
