"""Bounded sensitivity checks for workload, geometry, and warm-up choices."""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.research_sensitivity import workload as base_workload
from flash_sim.simulator import FlashSimulator

SEEDS = tuple(range(303001, 303011))
UTILIZATION = 0.70
MEASURED = 5000
BASE_GEOMETRY = (16, 32)
ALT_GEOMETRY = (32, 32)
WARMUPS = (0, 2500, 10000)


def make_addresses(seed: int, active: int, count: int, family: str) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if family == "uniform":
        return base_workload(rng, active, "uniform", count)
    if family == "hot_cold_80_10":
        return base_workload(rng, active, "hot_cold", count)
    if family == "hot_cold_90_05":
        hot = max(1, active // 20)
        base = rng.random(count)
        hot_choice = rng.random(count)
        hot_address = rng.random(count)
        hot_lbas = np.minimum((hot_address * hot).astype(int), hot - 1)
        cold_span = active - hot
        cold_lbas = hot + np.minimum((base * cold_span).astype(int), cold_span - 1)
        return np.where(hot_choice < 0.9, hot_lbas, cold_lbas)
    if family == "zipf_1_2":
        weights = 1 / np.arange(1, active + 1, dtype=float) ** 1.2
        weights /= weights.sum()
        return rng.choice(active, size=count, p=weights)
    raise ValueError(f"unknown workload family {family}")


def run_one(blocks: int, pages: int, warmup: int, family: str, seed: int) -> dict:
    total = blocks * pages
    active = round(total * UTILIZATION)
    sim = FlashSimulator(num_blocks=blocks, pages_per_block=pages,
                         gc_threshold_free_pages=pages)
    for lba in range(active):
        sim.write_logical_page(lba, ("initial", lba))
    addresses = make_addresses(seed, active, warmup + MEASURED, family)
    for i, lba in enumerate(addresses[:warmup]):
        sim.write_logical_page(int(lba), ("warmup", i))
    before = (sim.physical_page_writes, sim.gc_page_copies, sim.block_erasures)
    assert len(sim.l2p) == active == sim.total_valid_pages
    sim.check_invariants()
    for i, lba in enumerate(addresses[warmup:]):
        sim.write_logical_page(int(lba), ("measured", i))
    sim.check_invariants()
    host = sim.physical_page_writes - before[0]
    copies = sim.gc_page_copies - before[1]
    return {
        "geometry_blocks": blocks,
        "pages_per_block": pages,
        "active_pages": active,
        "utilization": UTILIZATION,
        "warmup_updates": warmup,
        "measured_updates": MEASURED,
        "workload": family,
        "seed": seed,
        "mapped_pages_after_warmup": len(sim.l2p),
        "mapped_pages_after_measurement": len(sim.l2p),
        "host_programs": host,
        "gc_copy_programs": copies,
        "program_amplification": (host + copies) / host,
    }


def main() -> None:
    # One factor varies at a time around the 70% / 16x32 / 5k warm-up design.
    cells = []
    for family in ("uniform", "hot_cold_80_10", "hot_cold_90_05", "zipf_1_2"):
        cells.extend(run_one(*BASE_GEOMETRY, 5000, family, seed) for seed in SEEDS)
    cells.extend(run_one(*ALT_GEOMETRY, 5000, family, seed)
                 for family in ("uniform", "hot_cold_80_10") for seed in SEEDS)
    for warmup in (0, 2500, 10000):
        cells.extend(run_one(*BASE_GEOMETRY, warmup, family, seed)
                     for family in ("uniform", "hot_cold_80_10") for seed in SEEDS)
    output = {
        "protocol": {
            "purpose": "bounded sensitivity analysis, not a confirmatory significance test",
            "seeds": list(SEEDS),
            "independent_seed_blocks": len(SEEDS),
            "utilization": UTILIZATION,
            "measured_updates": MEASURED,
            "base_geometry": {"blocks": BASE_GEOMETRY[0], "pages_per_block": BASE_GEOMETRY[1]},
            "alternative_geometry": {"blocks": ALT_GEOMETRY[0], "pages_per_block": ALT_GEOMETRY[1]},
            "warmup_values": list(WARMUPS),
            "workload_families": ["uniform", "hot_cold_80_10", "hot_cold_90_05", "zipf_1_2"],
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "runs": cells,
    }
    out = ROOT / "research/results/robustness_trials.json"
    out.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Wrote {len(cells)} sensitivity runs to {out}")


if __name__ == "__main__":
    main()
