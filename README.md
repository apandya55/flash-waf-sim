# FlashWAF: a page-mapped flash simulator

FlashWAF is a small Python model of page allocation, out-of-place updates, greedy garbage collection, and block erasure. The simulator helps inspect page-level write amplification in a controlled setting. It does not model NAND timing, persistent FTL metadata, power-loss recovery, or device endurance.

## Research result

The study measures program amplification in this simulator under equal full-page overwrites. It varies active logical-page utilization and the address distribution. The experiment uses 30 condition runs grouped into five paired pseudorandom seed blocks. Common random numbers pair latent draws across conditions, and the hot and cold address ranges are disjoint.

The paired hot/cold-minus-uniform contrasts are:

- 40% utilization: +0.19936, with a descriptive paired Student-t interval of [0.18603, 0.21269] at df=4.
- 70% utilization: -0.13604, with an interval of [-0.15308, -0.11900] at df=4.
- 85% utilization: -1.78292, with an interval of [-1.86718, -1.69866] at df=4.

These intervals describe variation across the five fixed simulation seed blocks. The result characterizes this allocator and workload generator. It does not describe a general physical law for NAND devices.

Earlier examples compared a direct path with a record buffer. The buffer discarded record addresses, so the two paths represented different logical states. The old 66x comparison and related durability claims are withdrawn. The audit in [research/AUDIT.md](research/AUDIT.md) records the reasons.

## Reproduce the study

The repository was tested with Python 3.12. It requires Python 3.9 or newer.

1. Create and activate a virtual environment:

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the runtime and test dependencies:

   ```sh
   python -m pip install -r requirements.txt
   python -m pip install -e '.[dev]'
   ```

3. Run all 35 tests:

   ```sh
   python -m pytest -q
   ```

4. Re-run the 30 seeded trials:

   ```sh
   python experiments/research_sensitivity.py
   ```

5. Recalculate the cell summaries, paired contrasts, intervals, and figure:

   ```sh
   python experiments/summarize_results.py
   ```

The raw trials are stored in `research/results/sensitivity_trials.json`. The derived summaries are stored in `research/results/summary.json`. The figure is `research/figures/program_amplification.png`. The full protocol appears in [research/METHODOLOGY.md](research/METHODOLOGY.md), and the validation record appears in [research/VALIDATION.md](research/VALIDATION.md).

## Use the simulator

```python
from flash_sim import FlashSimulator

sim = FlashSimulator(num_blocks=16, pages_per_block=32)
sim.write_logical_page(7, b"full-page payload")
assert sim.read_logical_page(7) == b"full-page payload"
sim.check_invariants()
```

`write_logical_page` represents one page-level logical write. The simulator does not model sub-page programming. `RingBuffer` remains an educational record packer with incomplete logical-address semantics. `PowerLossSimulator` reports bytes left in its volatile queue at an injected event; it does not restart the simulator or recover persistent state.

## Repository guide

- `flash_sim/` contains the simulator and supporting models.
- `tests/` contains the unit and invariant tests.
- `experiments/` contains the reproducible trial and summary scripts.
- `paper/` contains the LaTeX manuscript, bibliography, and compiled PDF.
- `research/` contains the audit, protocol, validation record, venue screen, and submission-readiness report.
- `CITATION.cff` contains citation metadata for archive deposits.

Generative AI tools were utilized for test generation, code refactoring, and drafting assistance; all simulation runs, mathematical derivations, and citations were verified by the author.

## License

The project uses the MIT License. See [LICENSE](LICENSE).
