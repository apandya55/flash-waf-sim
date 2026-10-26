# FlashWAF: a page-mapped flash simulator

FlashWAF is a Python simulator for page allocation, out-of-place logical writes, greedy garbage collection, and block erasure. It is a software model for inspecting page-program amplification. It does not model NAND timing, persistent FTL metadata, power-loss recovery, or device endurance.

## Current experiment

The primary experiment begins with every active logical address mapped, applies 5,000 warm-up updates, and measures the next 5,000 updates. It compares uniform and disjoint hot/cold workloads at equal mapped-page occupancy. Thirty paired seed blocks cover six conditions, for 180 runs. Common random numbers pair the latent random draws used to construct each condition's workload.

The hot/cold-minus-uniform program-amplification contrasts were:

- 40% occupancy: +0.32987, with a descriptive paired Student-t interval of [0.32665, 0.33310] at df=29.
- 70% occupancy: +0.60656, with an interval of [0.60054, 0.61258] at df=29.
- 85% occupancy: +0.80465, with an interval of [0.78676, 0.82253] at df=29.

These measurements describe this simulator and workload construction. They do not predict physical SSD behavior or establish a general result about NAND flash.

A separate 120-run sensitivity grid tests workload family, geometry, and warm-up length at 70% occupancy. It uses ten paired seed blocks per condition. The hot/cold 80/10-minus-uniform contrast stays positive across the tested warm-up lengths, from +0.50408 to +0.60486, and is +0.57378 in the larger geometry. It changes with workload family: +1.00414 for hot/cold 90/5, +0.77954 for Zipf exponent 1.2, and +0.60068 for the base hot/cold 80/10 case. These checks cover a small set of synthetic workloads and simulator settings.

The initial start-empty experiment is preserved in `research/results/baseline_start_empty_5seed/` and `research/figures/baseline_start_empty_5seed/` for audit history. Its sign reversal did not recur under the revised protocol. The two experiments use different initialization and measurement procedures, so their estimates are not pooled. The research audit explains the retired buffer and durability comparisons; those comparisons are not current project results.

## Install and reproduce

Use Python 3.9 or later. The checked environment used Python 3.12. NumPy and Matplotlib are runtime dependencies; pytest is included in the development extra.

1. Create and activate a virtual environment:

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the project and test dependencies:

   ```sh
   python -m pip install -e '.[dev]'
   ```

3. Run the test suite:

   ```sh
   python -m pytest -q
   ```

4. Regenerate the primary experiment, summary, and figure:

   ```sh
   python experiments/research_sensitivity.py
   python experiments/summarize_results.py
   ```

5. Regenerate the sensitivity experiment, summary, figure, and analytical comparison:

   ```sh
   python experiments/robustness_validation.py
   python experiments/summarize_robustness.py
   python experiments/analytical_reference.py
   ```

The primary raw trials and summary are in `research/results/sensitivity_trials.json` and `research/results/summary.json`. The sensitivity outputs are in `research/results/robustness_trials.json` and `research/results/robustness_summary.json`. Figures are in `research/figures/`. The runs are seeded and deterministic in the verified environment. The experiment uses 30 independent seed blocks, each covering all six primary conditions; it does not treat the 180 condition runs as independent replications.

See [research/METHODOLOGY.md](research/METHODOLOGY.md) for the protocol and [research/VALIDATION.md](research/VALIDATION.md) for the validation record. [research/AUDIT.md](research/AUDIT.md) preserves the historical audit and documents retired claims.

## Use the simulator

```python
from flash_sim import FlashSimulator

sim = FlashSimulator(num_blocks=16, pages_per_block=32)
sim.write_logical_page(7, b"full-page payload")
assert sim.read_logical_page(7) == b"full-page payload"
sim.check_invariants()
```

`write_logical_page` models one full-page logical write. The simulator does not model sub-page programming. `RingBuffer` is an educational record packer with incomplete logical-address semantics. `PowerLossSimulator` reports bytes left in its volatile queue after an injected event; it does not restart the simulator or recover persistent state.

## Repository contents

- `flash_sim/` contains the simulator and supporting models.
- `tests/` contains the unit and invariant tests.
- `experiments/` contains trial, summary, and figure-generation scripts.
- `paper/` contains the LaTeX source, bibliography, and compiled PDF for the bounded study.
- `research/` contains the methodology, results, validation record, and historical audit.
- `research/archive/legacy_exploratory_figures/` holds early plots that are not evidence for the current experiment.
- `CITATION.cff` and `.zenodo.json` provide citation and archive metadata.

Generative AI tools were utilized for test generation, code refactoring, and drafting assistance; all simulation runs, mathematical derivations, and citations were verified by the author.

## License

FlashWAF is distributed under the MIT License. See [LICENSE](LICENSE).
