"""Aggregate seeded experiment results and render the paper figure."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "research/results/sensitivity_trials.json").read_text())
rows = []
for util in (0.40, 0.70, 0.85):
    for locality in ("uniform", "hot_cold"):
        trials = [r for r in data["trials"] if r["utilization"] == util and r["locality"] == locality]
        vals = [r["program_amplification"] for r in trials]
        rows.append({"utilization": util, "locality": locality, "n": len(vals),
                     "mean_amplification": float(np.mean(vals)),
                     "sd_amplification": float(np.std(vals, ddof=1)),
                     "mean_gc_copies": float(np.mean([r["gc_copy_programs"] for r in trials])),
                     "mean_erasures": float(np.mean([r["block_erasures"] for r in trials]))})
(ROOT / "research/results/summary.json").write_text(json.dumps(rows, indent=2) + "\n")

fig, ax = plt.subplots(figsize=(6.7, 4.2))
for loc, marker, color, label in [
    ("uniform", "o", "#2457A7", "Uniform"),
    ("hot_cold", "s", "#B44A3A", "Hot/cold (80% to 10% hot set)"),
]:
    part = [r for r in rows if r["locality"] == loc]
    ax.errorbar([r["utilization"] * 100 for r in part],
                [r["mean_amplification"] for r in part],
                yerr=[r["sd_amplification"] for r in part],
                marker=marker, color=color, capsize=4, linewidth=2, label=label)
ax.set(xlabel="Active logical pages (% of physical pages)",
       ylabel="Modeled program amplification (programs/program)",
       title="Page-level FTL sensitivity (mean ± SD, 5 seeds)")
ax.set_xticks([40, 70, 85])
ax.grid(alpha=.25)
ax.legend(frameon=False)
fig.tight_layout()
out = ROOT / "research/figures/program_amplification.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=220)
plt.close(fig)
print(f"Wrote summary and {out}")
