# Resume bullets

- Built a Python page-mapped NAND flash simulator with out-of-place writes, greedy garbage collection, and program-amplification accounting; checked mapping and page-state invariants with 36 pytest tests.
- Ran 180 condition trials in 30 paired seed blocks, using common random numbers to compare uniform and disjoint hot/cold workloads at three mapped-page occupancy levels.
- Measured hot/cold-minus-uniform program-amplification contrasts of +0.32987 at 40% occupancy and +0.80465 at 85%, with paired Student-t intervals across 30 seed blocks (df=29).
- Packaged raw trial data, reproducible analysis scripts, sensitivity checks, and a compiled LaTeX study; documented the limits of the simulator and its synthetic workloads.
