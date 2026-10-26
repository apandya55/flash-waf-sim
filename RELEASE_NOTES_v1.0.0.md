# FlashWAF v1.0.0

FlashWAF v1.0.0 packages the page-mapped simulator, its tests, and the reproducible experiment materials.

## Included

- Page allocation, out-of-place logical writes, greedy garbage collection, and block erasure.
- A primary experiment with 180 condition runs across 30 paired seed blocks.
- A separate 120-run sensitivity grid covering selected workload families, geometries, and warm-up lengths.
- Raw results, analysis scripts, figures, the LaTeX study source, and an MIT license.
- Citation metadata in `CITATION.cff` and Zenodo metadata in `.zenodo.json`.

The README contains installation and reproduction commands. The test suite has 36 passing tests in the verified Python 3.12 environment.

## Scope

The measurements describe this simulator and its synthetic workloads. They do not predict physical SSD behavior. The project makes no claim of peer-reviewed publication or novel general scientific findings. The original start-empty data remain archived separately and are not pooled with the revised experiment.

## Installation

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
```

For experiment reproduction, follow the commands in `README.md` from a source checkout.
