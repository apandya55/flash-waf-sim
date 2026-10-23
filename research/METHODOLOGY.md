# Experimental methodology

Run from the repository root with Python 3.12, NumPy, and Matplotlib:

```sh
python3 -m pytest -q
python3 experiments/research_sensitivity.py
python3 experiments/summarize_results.py
```

The protocol uses 16 erase blocks × 32 pages (512 physical pages), 4,096-byte pages, a GC threshold of 32 free pages, and 5,000 full-page overwrites per run. Active logical-page counts are rounded from 40%, 70%, and 85% of physical pages. Uniform runs sample the active address space uniformly. Hot/cold runs send 80% of updates to a hot set containing 10% of active addresses and 20% to a disjoint cold set containing the rest. Five NumPy `default_rng` seeds (11, 23, 47, 89, 101) are paired across all six utilization-by-locality conditions.

The generator uses common random numbers: each seed creates latent uniform arrays used consistently across the six conditions, then maps those draws into the condition-specific workload. This corrects the earlier version, in which conditional random-number consumption and overlapping hot/cold address ranges made same-numbered seeds fail to provide a coherent paired design. The address sequences are not identical between conditions; the aligned entities are the latent draws. Each seed is one replication block, independent of the other seed streams under the pseudorandom generator. Thus there are 30 runs but only five independent blocks for paired locality and interaction contrasts. This estimates simulation variability under these configured distributions; it does not sample real drives or workload populations.

The outcome called **program amplification** is `(host-triggered page programs + GC copy page programs) / host-triggered page programs`, in page-programs per page-program. It excludes metadata, controller writes, NAND internal operations, and host bytes. Erasures are cumulative modeled block-erase operations; per-block erase counts are reported. Each trial checks L2P and page-state invariants. Summary means and sample standard deviations are derived directly from raw trial JSON. These workloads begin from an empty device, so results include startup and sustained GC behavior together; there is no claim of steady-state convergence.

Limitations: one logical address maps to one full physical page, no sub-page records or write buffer are present, and the allocator/GC policy is a small greedy abstraction. Results combine device startup and later GC behavior; no steady-state stopping rule was used. Results describe this implementation and these synthetic distributions only.
