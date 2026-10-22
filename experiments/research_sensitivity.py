"""Paired locality/utilization experiment with prepopulation and warm-up."""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash_sim.simulator import FlashSimulator


GEOMETRY_BLOCKS = 16
PAGES_PER_BLOCK = 32
UTILIZATIONS = (0.40, 0.70, 0.85)
LOCALITIES = ("uniform", "hot_cold")
SEEDS = tuple(range(202601, 202631))
WARMUP_UPDATES = 5000
MEASURED_UPDATES = 5000


def workload(rng: np.random.Generator, active: int, locality: str,
             count: int) -> np.ndarray:
    """Map common latent draws to a condition-specific address distribution."""
    # Draw the complete latent vector for every treatment so each seed uses
    # the same random-number streams regardless of which transformation runs.
    base_address_u = rng.random(count)
    hot_choice_u = rng.random(count)
    hot_address_u = rng.random(count)
    if locality == "uniform":
        return np.minimum((base_address_u * active).astype(int), active - 1)
    if locality != "hot_cold":
        raise ValueError(f"unknown locality: {locality}")
    hot = max(1, active // 10)
    cold_span = active - hot
    hot_addresses = np.minimum((hot_address_u * hot).astype(int), hot - 1)
    cold_addresses = hot + np.minimum((base_address_u * cold_span).astype(int), cold_span - 1)
    return np.where(hot_choice_u < 0.8, hot_addresses, cold_addresses)


def trial(utilization: float, locality: str, seed: int) -> dict:
    total = GEOMETRY_BLOCKS * PAGES_PER_BLOCK
    active = round(total * utilization)
    rng = np.random.default_rng(seed)
    # Every condition begins with the same deterministic logical-to-physical
    # population. All active LBAs are mapped before traffic is generated.
    sim = FlashSimulator(num_blocks=GEOMETRY_BLOCKS,
                         pages_per_block=PAGES_PER_BLOCK,
                         gc_threshold_free_pages=PAGES_PER_BLOCK)
    for lba in range(active):
        sim.write_logical_page(lba, data=("initial", lba))
    assert len(sim.l2p) == active
    assert sim.total_valid_pages == active
    sim.check_invariants()

    updates = workload(rng, active, locality,
                       WARMUP_UPDATES + MEASURED_UPDATES)
    warmup = updates[:WARMUP_UPDATES]
    measured = updates[WARMUP_UPDATES:]
    for i, lba in enumerate(warmup):
        sim.write_logical_page(int(lba), data=("warmup", seed, i))
    sim.check_invariants()
    warmup_counts = {
        "host_programs": sim.physical_page_writes,
        "gc_copy_programs": sim.gc_page_copies,
        "block_erasures": sim.block_erasures,
    }
    mapped_before = len(sim.l2p)
    valid_before = sim.total_valid_pages

    for i, lba in enumerate(measured):
        sim.write_logical_page(int(lba), data=("measured", seed, i))
    sim.check_invariants()
    host = sim.physical_page_writes - warmup_counts["host_programs"]
    gc_copies = sim.gc_page_copies - warmup_counts["gc_copy_programs"]
    erasures = sim.block_erasures - warmup_counts["block_erasures"]
    erase_counts = [block.erase_count for block in sim.blocks]
    return {
        "utilization": utilization,
        "configured_active_logical_pages": active,
        "mapped_pages_before_warmup": active,
        "mapped_pages_after_warmup": mapped_before,
        "valid_pages_after_warmup": valid_before,
        "mapped_pages_after_measurement": len(sim.l2p),
        "valid_pages_after_measurement": sim.total_valid_pages,
        "locality": locality,
        "seed": seed,
        "warmup_updates": WARMUP_UPDATES,
        "measured_updates": MEASURED_UPDATES,
        "host_programs": host,
        "gc_copy_programs": gc_copies,
        "total_page_programs": host + gc_copies,
        "block_erasures": erasures,
        "program_amplification": (host + gc_copies) / host,
        "erase_count_min_final": min(erase_counts),
        "erase_count_max_final": max(erase_counts),
        "erase_count_mean_final": sum(erase_counts) / len(erase_counts),
        "erase_count_sd_final": float(np.std(erase_counts, ddof=1)),
        "erase_counts_final": erase_counts,
    }


def main() -> None:
    results = [trial(u, loc, seed) for u in UTILIZATIONS
               for loc in LOCALITIES for seed in SEEDS]
    output = {
        "configuration": {
            "geometry_blocks": GEOMETRY_BLOCKS,
            "pages_per_block": PAGES_PER_BLOCK,
            "page_size_bytes": 4096,
            "gc_threshold_free_pages": PAGES_PER_BLOCK,
            "seeds": list(SEEDS),
            "paired_seed_blocks": len(SEEDS),
            "warmup_updates_per_trial": WARMUP_UPDATES,
            "measured_updates_per_trial": MEASURED_UPDATES,
            "initialization": "prepopulate every active LBA in ascending order",
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "trials": results,
    }
    path = ROOT / "research/results/sensitivity_trials.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Wrote {len(results)} trials ({len(SEEDS)} paired seed blocks) to {path}")


if __name__ == "__main__":
    main()
