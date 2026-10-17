"""Seeded page-level locality/utilization sensitivity experiment."""
from __future__ import annotations

import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash_sim.simulator import FlashSimulator


def trial(utilization: float, locality: str, seed: int, updates: int = 5000) -> dict:
    blocks, pages = 16, 32
    total = blocks * pages
    active = round(total * utilization)
    rng = np.random.default_rng(seed)
    if locality == "uniform":
        addresses = rng.integers(active, size=updates)
    else:
        hot = max(1, active // 10)
        choose_hot = rng.random(updates) < 0.8
        addresses = np.where(choose_hot, rng.integers(hot, size=updates),
                            rng.integers(active, size=updates))
    sim = FlashSimulator(num_blocks=blocks, pages_per_block=pages,
                         gc_threshold_free_pages=pages)
    for i, lba in enumerate(addresses):
        sim.write_logical_page(int(lba), data=(seed, i))
    sim.check_invariants()
    erase = [block.erase_count for block in sim.blocks]
    host = sim.physical_page_writes
    return {
        "utilization": utilization, "active_logical_pages": active,
        "locality": locality, "seed": seed, "host_programs": host,
        "gc_copy_programs": sim.gc_page_copies,
        "total_page_programs": host + sim.gc_page_copies,
        "block_erasures": sim.block_erasures,
        "program_amplification": (host + sim.gc_page_copies) / host,
        "erase_count_min": min(erase), "erase_count_max": max(erase),
        "erase_count_mean": sum(erase) / len(erase),
        "erase_count_sd": float(np.std(erase, ddof=1)),
        "erase_counts": erase,
    }


def main() -> None:
    results = [trial(u, loc, seed) for u in (0.40, 0.70, 0.85)
               for loc in ("uniform", "hot_cold") for seed in (11, 23, 47, 89, 101)]
    output = {"configuration": {"geometry_blocks": 16, "pages_per_block": 32,
               "page_size_bytes": 4096, "updates_per_trial": 5000,
               "gc_threshold_free_pages": 32, "seeds": [11, 23, 47, 89, 101],
               "python": platform.python_version(), "numpy": np.__version__},
              "trials": results}
    path = ROOT / "research/results/sensitivity_trials.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Wrote {len(results)} trials to {path}")
    for u in (0.40, 0.70, 0.85):
        for loc in ("uniform", "hot_cold"):
            values = [r["program_amplification"] for r in results
                      if r["utilization"] == u and r["locality"] == loc]
            print(f"util={u:.0%} locality={loc}: amplification mean={np.mean(values):.3f}, sd={np.std(values, ddof=1):.3f}")


if __name__ == "__main__":
    main()
