"""Summarize paired experiment results and render the manuscript figure."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "research/results/sensitivity_trials.json").read_text())
seeds = data["configuration"]["seeds"]
utilizations = (0.40, 0.70, 0.85)
localities = ("uniform", "hot_cold")
by_key = {(r["utilization"], r["locality"], r["seed"]): r
          for r in data["trials"]}

# Two-sided 95% Student-t critical value, df=29 (30 independent paired seeds).
t_critical = 2.045229642132703


def interval(values):
    values = np.asarray(values, dtype=float)
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    half = t_critical * sd / np.sqrt(len(values))
    return mean, sd, [mean - half, mean + half]


cells = []
for util in utilizations:
    for locality in localities:
        trials = [by_key[(util, locality, seed)] for seed in seeds]
        values = [r["program_amplification"] for r in trials]
        cells.append({
            "utilization": util,
            "locality": locality,
            "n_independent_seed_blocks": len(values),
            "mean_amplification": float(np.mean(values)),
            "sd_amplification": float(np.std(values, ddof=1)),
            "mean_gc_copies": float(np.mean([r["gc_copy_programs"] for r in trials])),
            "mean_erasures": float(np.mean([r["block_erasures"] for r in trials])),
        })

paired_effects = []
for util in utilizations:
    diffs = [by_key[(util, "hot_cold", seed)]["program_amplification"]
             - by_key[(util, "uniform", seed)]["program_amplification"]
             for seed in seeds]
    mean, sd, ci = interval(diffs)
    paired_effects.append({
        "utilization": util,
        "contrast": "hot_cold_minus_uniform",
        "paired_differences_by_seed": diffs,
        "n_independent_seed_blocks": len(diffs),
        "df": len(diffs) - 1,
        "mean": mean,
        "sd": sd,
        "ci95_t": ci,
    })

interaction_contrasts = []
for higher in utilizations[1:]:
    low = paired_effects[0]["paired_differences_by_seed"]
    high = next(e["paired_differences_by_seed"] for e in paired_effects
                if e["utilization"] == higher)
    diffs = [hi - lo for hi, lo in zip(high, low)]
    mean, sd, ci = interval(diffs)
    interaction_contrasts.append({
        "comparison": f"{higher:.0%}_minus_40%_locality_effect",
        "paired_differences_by_seed": diffs,
        "n_independent_seed_blocks": len(diffs),
        "df": len(diffs) - 1,
        "mean_difference_in_differences": mean,
        "sd": sd,
        "ci95_t": ci,
    })

summary = {
    "cell_summaries": cells,
    "paired_locality_effects": paired_effects,
    "interaction_contrasts": interaction_contrasts,
    "interval_note": (
        "Two-sided descriptive paired Student-t intervals across 30 independent "
        "pseudorandom seed blocks (df=29). These characterize this fixed simulator "
        "and synthetic workload design, not device or workload populations."
    ),
}
(ROOT / "research/results/summary.json").write_text(json.dumps(summary, indent=2) + "\n")

fig, ax = plt.subplots(figsize=(6.7, 4.2))
for loc, marker, color, label in [
    ("uniform", "o", "#2457A7", "Uniform"),
    ("hot_cold", "s", "#B44A3A", "Hot/cold (80% to 10% hot set)"),
]:
    part = [r for r in cells if r["locality"] == loc]
    ax.errorbar([r["utilization"] * 100 for r in part],
                [r["mean_amplification"] for r in part],
                yerr=[r["sd_amplification"] for r in part],
                marker=marker, color=color, capsize=4, linewidth=2, label=label)
ax.set(xlabel="Mapped logical-page occupancy (% of physical pages)",
       ylabel="Measured program amplification (programs/program)",
       title="Prepopulated page-mapped simulator (mean ± SD, 30 seed blocks)")
ax.set_xticks([40, 70, 85])
ax.grid(alpha=.25)
ax.legend(frameon=False)
fig.tight_layout()
out = ROOT / "research/figures/program_amplification.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=220)
plt.close(fig)
print(f"Wrote summary and {out}")
