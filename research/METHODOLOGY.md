# Experimental methodology

Run from the repository root with Python 3.12, NumPy, and Matplotlib:

```sh
python3 -m pytest -q
python3 experiments/research_sensitivity.py
python3 experiments/summarize_results.py
```

The protocol uses 16 erase blocks × 32 pages (512 physical pages), 4,096-byte pages, a GC threshold of 32 free pages, and 5,000 full-page overwrites per trial. Active logical-page counts are rounded from 40%, 70%, and 85% of physical pages. Uniform trials sample the active address space uniformly. Hot/cold trials send 80% of updates to a hot set of 10% of active addresses and 20% to a uniform draw across the entire active range. Five independent NumPy `default_rng` seeds (11, 23, 47, 89, 101) are paired across every condition.

The outcome called **program amplification** is `(host-triggered page programs + GC copy page programs) / host-triggered page programs`, in page-programs per page-program. It excludes metadata, controller writes, NAND internal operations, and host bytes. Erasures are cumulative modeled block-erase operations; per-block erase counts are reported. Each trial checks L2P and page-state invariants. Summary means and sample standard deviations are derived directly from raw trial JSON. These workloads begin from an empty device, so results include startup and sustained GC behavior together; there is no claim of steady-state convergence.

Limitations: one logical address maps to one full physical page, no sub-page records or write buffer are present, and the allocator/GC policy is a small greedy abstraction. A hot/cold sample can select a “cold” address that is also in the hot range because the cold draw is from the full active range; the mixture therefore means 80% hot-set-biased plus 20% uniform, not disjoint hot/cold populations. Results describe this implementation only.
