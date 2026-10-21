"""Summarize the predeclared, bounded robustness grid and make its figure."""
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
# Two-sided 95% Student-t critical value for df=9 (ten paired seed blocks).
T_CRITICAL_DF9 = 2.262157162740992
raw = json.loads((ROOT / "research/results/robustness_trials.json").read_text())
groups = defaultdict(list)
for row in raw["runs"]:
    key = (row["geometry_blocks"], row["pages_per_block"],
           row["warmup_updates"], row["workload"])
    groups[key].append(row["program_amplification"])

cells = []
for key, vals in sorted(groups.items()):
    blocks, ppb, warmup, workload = key
    cells.append({
        "geometry_blocks": blocks,
        "pages_per_block": ppb,
        "warmup_updates": warmup,
        "workload": workload,
        "n_seed_blocks": len(vals),
        "mean_program_amplification": statistics.mean(vals),
        "sd_across_seed_blocks": statistics.stdev(vals),
        "min": min(vals),
        "max": max(vals),
    })

seed_ids = raw["protocol"]["seeds"]
contrasts = []
for geom, warmup in [((16, 32), 5000), ((32, 32), 5000),
                     ((16, 32), 0), ((16, 32), 2500), ((16, 32), 10000)]:
    for treatment in ("hot_cold_80_10", "hot_cold_90_05", "zipf_1_2"):
        uniform = {(r["seed"]): r["program_amplification"] for r in raw["runs"]
                   if (r["geometry_blocks"], r["pages_per_block"]) == geom
                   and r["warmup_updates"] == warmup and r["workload"] == "uniform"}
        values = {(r["seed"]): r["program_amplification"] for r in raw["runs"]
                  if (r["geometry_blocks"], r["pages_per_block"]) == geom
                  and r["warmup_updates"] == warmup and r["workload"] == treatment}
        if all(seed in uniform and seed in values for seed in seed_ids):
            diffs = [values[seed] - uniform[seed] for seed in seed_ids]
            mean_diff = statistics.mean(diffs)
            sd_diff = statistics.stdev(diffs)
            half_width = T_CRITICAL_DF9 * sd_diff / math.sqrt(len(diffs))
            contrasts.append({
                "geometry": f"{geom[0]}x{geom[1]}",
                "warmup_updates": warmup,
                "contrast": f"{treatment}_minus_uniform",
                "n_paired_seed_blocks": len(diffs),
                "mean_paired_difference": mean_diff,
                "sd_paired_difference": sd_diff,
                "df": len(diffs) - 1,
                "ci95_paired_t": [mean_diff - half_width, mean_diff + half_width],
                "min_paired_difference": min(diffs),
                "max_paired_difference": max(diffs),
            })

summary = {
    "purpose": raw["protocol"]["purpose"],
    "seed_blocks": len(seed_ids),
    "cell_summaries": cells,
    "paired_sensitivity_contrasts": contrasts,
    "interpretation": (
        "Descriptive sensitivity checks at 70% occupancy. Paired t intervals use "
        "df=9 and describe seed-block variation for each fixed simulator condition; "
        "they are not population intervals. One design factor varies at a time "
        "where applicable."
    ),
}
(ROOT / "research/results/robustness_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

fig, axes = plt.subplots(1, 3, figsize=(10, 3.7), sharey=True)
panels = [
    ("Workload family", [c for c in cells if c["geometry_blocks"] == 16 and c["warmup_updates"] == 5000]),
    ("Geometry", [c for c in cells if c["workload"] in ("uniform", "hot_cold_80_10") and c["warmup_updates"] == 5000]),
    ("Warm-up updates", [c for c in cells if c["geometry_blocks"] == 16 and c["workload"] in ("uniform", "hot_cold_80_10")]),
]
colors = {"uniform": "#2457A7", "hot_cold_80_10": "#B44A3A",
          "hot_cold_90_05": "#8C5AA7", "zipf_1_2": "#508C62"}
labels = {"uniform": "Uniform", "hot_cold_80_10": "Hot/cold 80/10",
          "hot_cold_90_05": "Hot/cold 90/5", "zipf_1_2": "Zipf 1.2"}
for ax, (title, part) in zip(axes, panels):
    if title == "Workload family":
        order = ["uniform", "hot_cold_80_10", "hot_cold_90_05", "zipf_1_2"]
        for i, workload in enumerate(order):
            row = next(c for c in part if c["workload"] == workload)
            ax.errorbar(i, row["mean_program_amplification"],
                        yerr=row["sd_across_seed_blocks"], fmt="o",
                        color=colors[workload], capsize=3)
        ax.set_xticks(range(len(order)), [labels[w] for w in order], rotation=30, ha="right")
    elif title == "Geometry":
        for i, workload in enumerate(("uniform", "hot_cold_80_10")):
            rows = sorted((c for c in part if c["workload"] == workload),
                          key=lambda c: c["geometry_blocks"])
            for j, row in enumerate(rows):
                x = i * 3 + j
                ax.errorbar(x, row["mean_program_amplification"],
                            yerr=row["sd_across_seed_blocks"], fmt="o",
                            color=colors[workload], capsize=3)
        ax.set_xticks([0, 1, 3, 4], ["16x32", "32x32", "16x32", "32x32"], rotation=30)
        ax.text(0.5, 0.02, "uniform", transform=ax.transAxes, ha="center", fontsize=8)
        ax.text(0.86, 0.02, "hot/cold", transform=ax.transAxes, ha="center", fontsize=8)
    else:
        for workload in ("uniform", "hot_cold_80_10"):
            rows = sorted((c for c in part if c["workload"] == workload),
                          key=lambda c: c["warmup_updates"])
            ax.errorbar([r["warmup_updates"] for r in rows],
                        [r["mean_program_amplification"] for r in rows],
                        yerr=[r["sd_across_seed_blocks"] for r in rows],
                        marker="o", color=colors[workload], capsize=3, label=labels[workload])
        ax.set_xticks([0, 2500, 5000, 10000])
        ax.legend(frameon=False, fontsize=7)
    ax.set_title(title)
    ax.grid(alpha=.2)
    ax.tick_params(axis="x", labelsize=7)
axes[0].set_ylabel("Measured program amplification\n(mean ± SD, 10 seed blocks)")
fig.suptitle("Sensitivity at 70% mapped occupancy, 5,000 measured updates")
fig.tight_layout()
out = ROOT / "research/figures/robustness_sensitivity.png"
fig.savefig(out, dpi=220)
plt.close(fig)
print(f"Wrote {ROOT / 'research/results/robustness_summary.json'} and {out}")
