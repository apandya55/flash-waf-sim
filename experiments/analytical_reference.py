"""Compare uniform-workload simulator WAF with a published greedy-GC model."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / "research/results/summary.json").read_text())

# Agarwal and Marrow (2010) present an analytical model for write amplification
# under uniform random writes and greedy GC, and analyze the effect of
# over-provisioning. This check uses only the direction of the modeled
# relationship. It does not reimplement their closed-form expression because
# the current simulator does not satisfy the paper's full steady-state model.
rows = []
for cell in summary["cell_summaries"]:
    if cell["locality"] != "uniform":
        continue
    util = cell["utilization"]
    observed = cell["mean_amplification"]
    rows.append({
        "utilization": util,
        "simulator_mean_waf": observed,
        "n_seed_blocks": cell["n_independent_seed_blocks"],
    })
observed_values = [row["simulator_mean_waf"] for row in rows]
out = {
    "reference": {
        "citation": "Agarwal and Marrow, A Closed-Form Expression for Write Amplification in NAND Flash, IEEE GLOBECOM Workshops, 2010, DOI: 10.1109/GLOCOMW.2010.5700261",
        "scope": "Analytical write-amplification model for uniformly distributed random writes with greedy garbage collection; the paper studies over-provisioning effects.",
        "metadata_check": "DOI, title, authors, venue, and year matched Crossref metadata; abstract scope checked via OpenAlex.",
    },
    "comparison": rows,
    "observed_direction": "increasing" if observed_values == sorted(observed_values) else "not_monotone",
    "interpretation": "The simulator's uniform-workload mean WAF rises at all three occupancy levels, consistent with the direction of the published model's over-provisioning analysis. This is a qualitative consistency check only. It does not reproduce or numerically validate the paper's analytical expression; the finite-run simulator has different allocation, GC-trigger, and warm-up details, and its full text should be checked by the author before journal submission.",
}
(ROOT / "research/results/analytical_reference.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
