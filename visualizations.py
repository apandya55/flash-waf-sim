"""Phase 5: Comprehensive Visualizations & Extended Experiments.

Generates 8 publication-quality figures exploring the full design space of the
flash-waf-sim study. Each figure is produced by a dedicated function; main()
orchestrates them all and saves PNGs to the figures/ directory.

Figures:
    1. WAF vs. Buffer Size (log-scale diminishing-returns curve)
    2. Cumulative Block Erasure Timeline (unbuffered vs. buffered over workload progress)
    3. GC Overhead Breakdown (stacked bar: host writes vs. GC copies by buffer size)
    4. Working Set Size Sensitivity (WAF & erasures vs. num_lbas, dual y-axis)
    5. Durability vs. WAF Pareto Frontier (scatter + annotated trade-off)
    6. Power Loss Data Loss Distribution (box plot across multiple random seeds)
    7. Page State Evolution Snapshots (4-panel 64x64 grid at 25/50/75/100% workload)
    8. LBA Access Frequency Heatmap (hot/cold write pattern visualization)
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np

from benchmark_phase3 import generate_workload
from flash_sim.buffer import RingBuffer
from flash_sim.durability import PowerLossSimulator
from flash_sim.models import PageState
from flash_sim.simulator import FlashSimulator


# ── Global style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "figure.facecolor": "white",
    "savefig.dpi": 180,
    "savefig.bbox": "tight",
})

FIGURES_DIR = os.path.join(os.path.dirname(__file__) or ".", "figures")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 1: WAF vs. Buffer Size Curve
# ═══════════════════════════════════════════════════════════════════════════════

def fig1_waf_vs_buffer_size(workload: List[Tuple[int, bytes]]) -> str:
    """Sweep buffer capacity and plot WAF on a log scale."""
    buffer_sizes = [1, 2, 4, 8, 16, 32, 64, 128]
    wafs: List[float] = []
    erasures: List[int] = []

    for cap in buffer_sizes:
        sim = FlashSimulator(num_blocks=64, pages_per_block=64)
        buf = RingBuffer(flash_sim=sim, capacity_records=cap,
                         record_size_bytes=128, page_size_bytes=4096)
        for lba, data in workload:
            buf.push(record=data, lba=lba)
        buf.flush()

        host_bytes = len(workload) * 128
        phys_bytes = (sim.physical_page_writes + sim.gc_page_copies) * 4096
        wafs.append(phys_bytes / host_bytes)
        erasures.append(sim.block_erasures)

    fig, ax1 = plt.subplots(figsize=(10, 6))

    color_waf = "#2563EB"
    color_era = "#DC2626"

    ax1.set_xlabel("Buffer Capacity (records × 128 B)")
    ax1.set_ylabel("Write Amplification Factor (WAF)", color=color_waf)
    line1 = ax1.plot(buffer_sizes, wafs, "o-", color=color_waf, linewidth=2.5,
                     markersize=8, label="WAF", zorder=5)
    ax1.set_yscale("log")
    ax1.tick_params(axis="y", labelcolor=color_waf)
    ax1.set_xticks(buffer_sizes)
    ax1.set_xticklabels([f"{s}\n({s*128} B)" for s in buffer_sizes],
                        fontsize=8, rotation=0)

    # Annotate the key WAF values
    for i, (x, y) in enumerate(zip(buffer_sizes, wafs)):
        offset = (0, 12) if i < len(buffer_sizes) - 1 else (0, -18)
        ax1.annotate(f"{y:.1f}×", (x, y), textcoords="offset points",
                     xytext=offset, ha="center", fontsize=8, color=color_waf,
                     fontweight="bold")

    ax2 = ax1.twinx()
    ax2.set_ylabel("Block Erasures (P/E Cycles)", color=color_era)
    line2 = ax2.bar([s + 0.3 for s in buffer_sizes], erasures, width=1.5,
                    alpha=0.35, color=color_era, label="Block Erasures", zorder=2)
    ax2.tick_params(axis="y", labelcolor=color_era)

    # Add a horizontal reference at WAF=1.0
    ax1.axhline(y=1.0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax1.text(buffer_sizes[-1] + 2, 1.0, "WAF = 1.0\n(theoretical min)",
             va="center", fontsize=8, color="gray")

    lines = line1 + [line2]
    labels = [l.get_label() for l in line1] + ["Block Erasures"]
    ax1.legend(lines, labels, loc="upper right", fontsize=9)

    ax1.set_title("WAF vs. Buffer Size — Diminishing Returns Curve\n"
                   "25,000 random 128 B updates across 3,200 LBAs")
    fig.tight_layout()

    path = os.path.join(FIGURES_DIR, "fig1_waf_vs_buffer_size.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2: Cumulative Block Erasure Timeline
# ═══════════════════════════════════════════════════════════════════════════════

def fig2_erasure_timeline(workload: List[Tuple[int, bytes]]) -> str:
    """Track cumulative erasures over workload progress for unbuffered vs. buffered."""
    sample_interval = 250  # Sample every 250 writes
    total = len(workload)
    checkpoints = list(range(sample_interval, total + 1, sample_interval))

    # Unbuffered run with instrumentation
    sim_unbuf = FlashSimulator(num_blocks=64, pages_per_block=64)
    unbuf_erasures: List[int] = []
    unbuf_gc_copies: List[int] = []
    for i, (lba, data) in enumerate(workload):
        sim_unbuf.write_logical_page(lba=lba, data=data)
        if (i + 1) in checkpoints or (i + 1) == total:
            if (i + 1) % sample_interval == 0 or (i + 1) == total:
                unbuf_erasures.append(sim_unbuf.block_erasures)
                unbuf_gc_copies.append(sim_unbuf.gc_page_copies)

    # Buffered run with instrumentation
    sim_buf = FlashSimulator(num_blocks=64, pages_per_block=64)
    buf = RingBuffer(flash_sim=sim_buf, capacity_records=32,
                     record_size_bytes=128, page_size_bytes=4096)
    buf_erasures: List[int] = []
    buf_gc_copies: List[int] = []
    for i, (lba, data) in enumerate(workload):
        buf.push(record=data, lba=lba)
        if (i + 1) in checkpoints or (i + 1) == total:
            if (i + 1) % sample_interval == 0 or (i + 1) == total:
                buf_erasures.append(sim_buf.block_erasures)
                buf_gc_copies.append(sim_buf.gc_page_copies)
    buf.flush()

    x = checkpoints[:len(unbuf_erasures)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left: cumulative erasures
    ax1.plot(x, unbuf_erasures, "-", color="#DC2626", linewidth=2.2,
             label="Unbuffered")
    ax1.plot(x, buf_erasures, "-", color="#059669", linewidth=2.2,
             label="Ring-Buffered (32 rec)")
    ax1.fill_between(x, unbuf_erasures, alpha=0.12, color="#DC2626")
    ax1.fill_between(x, buf_erasures, alpha=0.12, color="#059669")
    ax1.set_xlabel("Host Updates Issued")
    ax1.set_ylabel("Cumulative Block Erasures")
    ax1.set_title("Cumulative Block Erasures\nover Workload Progress")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Right: cumulative GC copies
    ax2.plot(x, unbuf_gc_copies, "-", color="#DC2626", linewidth=2.2,
             label="Unbuffered")
    ax2.plot(x, buf_gc_copies, "-", color="#059669", linewidth=2.2,
             label="Ring-Buffered (32 rec)")
    ax2.fill_between(x, unbuf_gc_copies, alpha=0.12, color="#DC2626")
    ax2.fill_between(x, buf_gc_copies, alpha=0.12, color="#059669")
    ax2.set_xlabel("Host Updates Issued")
    ax2.set_ylabel("Cumulative GC Page Copies")
    ax2.set_title("Cumulative GC Overhead\nover Workload Progress")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.suptitle("Wear Accumulation Timeline — Unbuffered vs. Ring-Buffered",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()

    path = os.path.join(FIGURES_DIR, "fig2_erasure_timeline.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3: GC Overhead Stacked Bar
# ═══════════════════════════════════════════════════════════════════════════════

def fig3_gc_overhead_breakdown(workload: List[Tuple[int, bytes]]) -> str:
    """Stacked bar: host writes vs GC copies for each buffer size."""
    buffer_sizes = [1, 4, 8, 16, 32, 64, 128]
    host_writes: List[int] = []
    gc_copies: List[int] = []
    labels: List[str] = []

    for cap in buffer_sizes:
        sim = FlashSimulator(num_blocks=64, pages_per_block=64)
        buf = RingBuffer(flash_sim=sim, capacity_records=cap,
                         record_size_bytes=128, page_size_bytes=4096)
        for lba, data in workload:
            buf.push(record=data, lba=lba)
        buf.flush()

        host_writes.append(sim.physical_page_writes)
        gc_copies.append(sim.gc_page_copies)
        labels.append(f"{cap} rec\n({cap * 128} B)")

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(buffer_sizes))
    width = 0.55

    bars_host = ax.bar(x, host_writes, width, label="Host Page Writes",
                       color="#2563EB", edgecolor="white", linewidth=0.8)
    bars_gc = ax.bar(x, gc_copies, width, bottom=host_writes,
                     label="GC Page Copies (overhead)", color="#F59E0B",
                     edgecolor="white", linewidth=0.8)

    # Percentage labels
    for i, (hw, gc) in enumerate(zip(host_writes, gc_copies)):
        total = hw + gc
        if gc > 0:
            pct = gc / total * 100
            ax.text(i, total + 200, f"{pct:.0f}% GC", ha="center",
                    fontsize=8, fontweight="bold", color="#92400E")
        else:
            ax.text(i, total + 200, "0% GC", ha="center",
                    fontsize=8, fontweight="bold", color="#059669")

    ax.set_xlabel("Buffer Capacity")
    ax.set_ylabel("Total Physical Page Operations")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.legend(loc="upper right", fontsize=10)
    ax.set_title("GC Overhead Breakdown by Buffer Size\n"
                 "Host writes (useful) vs. GC copies (wasted I/O)")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, "fig3_gc_overhead_breakdown.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 4: Working Set Size Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════

def fig4_working_set_sensitivity() -> str:
    """Vary num_lbas and measure WAF + erasures for unbuffered and buffered."""
    lba_counts = [100, 200, 400, 800, 1600, 3200]
    num_updates = 25000

    unbuf_wafs: List[float] = []
    buf_wafs: List[float] = []
    unbuf_erasures: List[int] = []
    buf_erasures: List[int] = []

    for n_lbas in lba_counts:
        wl = generate_workload(num_updates=num_updates, record_size=128,
                               num_lbas=n_lbas, seed=42)

        # Unbuffered
        sim_u = FlashSimulator(num_blocks=64, pages_per_block=64)
        for lba, data in wl:
            sim_u.write_logical_page(lba=lba, data=data)
        hb = num_updates * 128
        pb = (sim_u.physical_page_writes + sim_u.gc_page_copies) * 4096
        unbuf_wafs.append(pb / hb)
        unbuf_erasures.append(sim_u.block_erasures)

        # Buffered
        sim_b = FlashSimulator(num_blocks=64, pages_per_block=64)
        buf = RingBuffer(flash_sim=sim_b, capacity_records=32,
                         record_size_bytes=128, page_size_bytes=4096)
        for lba, data in wl:
            buf.push(record=data, lba=lba)
        buf.flush()
        pb_b = (sim_b.physical_page_writes + sim_b.gc_page_copies) * 4096
        buf_wafs.append(pb_b / hb)
        buf_erasures.append(sim_b.block_erasures)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left: WAF comparison
    ax1.plot(lba_counts, unbuf_wafs, "o-", color="#DC2626", linewidth=2.2,
             markersize=7, label="Unbuffered WAF")
    ax1.plot(lba_counts, buf_wafs, "s-", color="#059669", linewidth=2.2,
             markersize=7, label="Ring-Buffered WAF")
    ax1.set_xlabel("Working Set Size (unique LBAs)")
    ax1.set_ylabel("Write Amplification Factor (WAF)")
    ax1.set_title("WAF vs. Working Set Size")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale("log")

    # Utilization percentage annotations
    for i, n in enumerate(lba_counts):
        util_pct = n / 4096 * 100
        ax1.annotate(f"{util_pct:.0f}%", (n, unbuf_wafs[i]),
                     textcoords="offset points", xytext=(0, 10),
                     ha="center", fontsize=7, color="#7F1D1D")

    # Right: erasure comparison
    ax2.bar([x - 0.15 for x in range(len(lba_counts))],
            unbuf_erasures, width=0.3, color="#DC2626", label="Unbuffered",
            alpha=0.85, edgecolor="white")
    ax2.bar([x + 0.15 for x in range(len(lba_counts))],
            buf_erasures, width=0.3, color="#059669", label="Ring-Buffered",
            alpha=0.85, edgecolor="white")
    ax2.set_xlabel("Working Set Size (unique LBAs)")
    ax2.set_ylabel("Block Erasures")
    ax2.set_xticks(range(len(lba_counts)))
    ax2.set_xticklabels([str(n) for n in lba_counts])
    ax2.set_title("Block Erasures vs. Working Set Size")
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("Working Set Size Sensitivity Analysis\n"
                 "25,000 updates × 128 B across varying LBA address spaces",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()

    path = os.path.join(FIGURES_DIR, "fig4_working_set_sensitivity.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5: Durability vs. WAF Pareto Frontier
# ═══════════════════════════════════════════════════════════════════════════════

def fig5_durability_pareto() -> str:
    """Scatter plot of durability rate vs WAF_committed with Pareto annotation."""
    num_updates = 25000
    num_crashes = 50
    seed = 42

    workload = generate_workload(num_updates=num_updates, record_size=128,
                                 num_lbas=3200, seed=seed)
    rng = np.random.RandomState(seed)
    crash_indices = sorted(
        rng.choice(range(100, num_updates - 100), size=num_crashes, replace=False).tolist()
    )

    policies = [
        ("Direct Unbuffered\n(128 B)", 1),
        ("1-Page Buffer\n(4 KiB)", 32),
        ("2-Page Buffer\n(8 KiB)", 64),
        ("4-Page Buffer\n(16 KiB)", 128),
    ]

    sim_power = PowerLossSimulator(num_blocks=64, pages_per_block=64)
    waf_vals: List[float] = []
    dur_vals: List[float] = []
    labels: List[str] = []
    buf_sizes: List[int] = []

    for name, cap in policies:
        res, _ = sim_power.evaluate_policy(
            policy_name=name, capacity_records=cap,
            workload=workload, crash_indices=crash_indices,
        )
        waf_vals.append(res.waf_committed)
        dur_vals.append(res.durability_rate)
        labels.append(name)
        buf_sizes.append(cap * 128)

    fig, ax = plt.subplots(figsize=(9, 7))

    colors = ["#DC2626", "#2563EB", "#7C3AED", "#D97706"]
    sizes = [180, 180, 180, 180]

    for i, (w, d, lbl, c) in enumerate(zip(waf_vals, dur_vals, labels, colors)):
        ax.scatter(w, d, s=sizes[i], c=c, zorder=5, edgecolors="white",
                   linewidth=2)
        # Position labels to avoid overlap
        ha = "left" if w < 30 else "right"
        offset_x = 1.2 if w < 30 else -1.2
        ax.annotate(lbl, (w, d), textcoords="offset points",
                    xytext=(15 if ha == "left" else -15, -5),
                    fontsize=9, fontweight="bold", color=c, ha=ha,
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.2))

    # Connect points with Pareto frontier line
    sorted_pts = sorted(zip(waf_vals, dur_vals), key=lambda p: p[0])
    ax.plot([p[0] for p in sorted_pts], [p[1] for p in sorted_pts],
            "--", color="gray", alpha=0.5, linewidth=1.5, zorder=2)

    # Quadrant annotation
    ax.axhline(y=97, color="#059669", linestyle=":", alpha=0.4, linewidth=1)
    ax.axvline(x=2.0, color="#059669", linestyle=":", alpha=0.4, linewidth=1)

    ax.fill_between([0, 2.0], 97, 101, alpha=0.08, color="#059669", zorder=1)
    ax.text(1.5, 100.2, "✓ Sweet Spot\n(Low WAF, High Durability)",
            fontsize=8, color="#059669", ha="center", va="top",
            fontstyle="italic")

    ax.set_xlabel("WAF (Committed Bytes) →  Higher = More Flash Wear",
                  fontsize=11)
    ax.set_ylabel("Durability Rate (%) →  Higher = Less Data Loss Risk",
                  fontsize=11)
    ax.set_title("Durability vs. WAF Trade-Off — Pareto Frontier\n"
                 "50 sudden power-loss events across 25,000 updates")
    ax.set_xlim(0, max(waf_vals) * 1.15)
    ax.set_ylim(min(dur_vals) - 2, 101)
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, "fig5_durability_pareto.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 6: Power Loss Data Loss Distribution (Box Plot)
# ═══════════════════════════════════════════════════════════════════════════════

def fig6_power_loss_boxplot() -> str:
    """Box plot of per-crash byte loss across 10 random seeds × 4 policies."""
    num_updates = 25000
    num_crashes = 50
    seeds = list(range(42, 52))  # 10 seeds

    policies = [
        ("Direct Unbuffered (128 B)", 1),
        ("1-Page Buffer (4 KiB)", 32),
        ("2-Page Buffer (8 KiB)", 64),
        ("4-Page Buffer (16 KiB)", 128),
    ]

    # Collect mean loss per seed for each policy
    all_data: Dict[str, List[float]] = {name: [] for name, _ in policies}

    for seed in seeds:
        workload = generate_workload(num_updates=num_updates, record_size=128,
                                     num_lbas=3200, seed=seed)
        rng = np.random.RandomState(seed)
        crash_indices = sorted(
            rng.choice(range(100, num_updates - 100), size=num_crashes, replace=False).tolist()
        )

        sim_power = PowerLossSimulator(num_blocks=64, pages_per_block=64)
        for name, cap in policies:
            res, _ = sim_power.evaluate_policy(
                policy_name=name, capacity_records=cap,
                workload=workload, crash_indices=crash_indices,
            )
            all_data[name].append(res.mean_lost_bytes)

    fig, ax = plt.subplots(figsize=(10, 6))

    data_arrays = [all_data[name] for name, _ in policies]
    short_labels = ["Unbuffered\n128 B", "1-Page\n4 KiB", "2-Page\n8 KiB", "4-Page\n16 KiB"]
    colors = ["#059669", "#2563EB", "#7C3AED", "#DC2626"]

    bp = ax.boxplot(data_arrays, labels=short_labels, patch_artist=True,
                    widths=0.45, showmeans=True,
                    meanprops=dict(marker="D", markerfacecolor="white",
                                   markeredgecolor="black", markersize=6),
                    medianprops=dict(color="white", linewidth=2),
                    flierprops=dict(marker="o", markerfacecolor="#9CA3AF",
                                    markersize=5, alpha=0.7))

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    # Overlay individual data points (jittered)
    rng_jitter = np.random.RandomState(99)
    for i, (arr, c) in enumerate(zip(data_arrays, colors)):
        jitter = rng_jitter.uniform(-0.1, 0.1, size=len(arr))
        ax.scatter([i + 1 + j for j in jitter], arr, s=30, color=c,
                   edgecolors="white", linewidth=0.8, alpha=0.9, zorder=5)

    ax.set_ylabel("Mean Bytes Lost per Power-Loss Event (B)")
    ax.set_title("Data Loss Distribution Across 10 Random Seeds\n"
                 "50 power-loss events per seed, 25,000 updates × 128 B")
    ax.grid(axis="y", alpha=0.3)

    # Add risk zone annotation
    ax.axhspan(0, 10, alpha=0.06, color="#059669", zorder=0)
    ax.text(0.55, 5, "Zero-loss zone", fontsize=8, color="#059669",
            fontstyle="italic", va="center")

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, "fig6_power_loss_boxplot.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 7: Page State Evolution Snapshots
# ═══════════════════════════════════════════════════════════════════════════════

def fig7_page_state_evolution(workload: List[Tuple[int, bytes]]) -> str:
    """4-panel snapshots of 64×64 page state grid at 25/50/75/100% workload."""
    total = len(workload)
    checkpoints = [total // 4, total // 2, 3 * total // 4, total]
    titles = ["25% Workload", "50% Workload", "75% Workload", "100% Workload"]

    # Map: FREE=0, VALID=1, INVALID=2
    state_map = {PageState.FREE: 0, PageState.VALID: 1, PageState.INVALID: 2}
    cmap = mcolors.ListedColormap(["#E5E7EB", "#2563EB", "#DC2626"])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    snapshots: List[np.ndarray] = []

    sim = FlashSimulator(num_blocks=64, pages_per_block=64)
    cp_idx = 0

    for i, (lba, data) in enumerate(workload):
        sim.write_logical_page(lba=lba, data=data)

        if cp_idx < len(checkpoints) and (i + 1) == checkpoints[cp_idx]:
            grid = np.zeros((64, 64), dtype=int)
            for b_idx, block in enumerate(sim.blocks):
                for p_idx, page in enumerate(block.pages):
                    grid[b_idx, p_idx] = state_map[page.state]
            snapshots.append(grid)
            cp_idx += 1

    fig, axes = plt.subplots(2, 2, figsize=(13, 11))

    for idx, (ax, grid, title) in enumerate(zip(axes.flat, snapshots, titles)):
        ax.imshow(grid, cmap=cmap, norm=norm, aspect="auto",
                  interpolation="nearest")
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("Page Index (0–63)")
        ax.set_ylabel("Block Index (0–63)")

        # Summary stats
        n_free = int(np.sum(grid == 0))
        n_valid = int(np.sum(grid == 1))
        n_invalid = int(np.sum(grid == 2))
        pct_txt = f"Free: {n_free} | Valid: {n_valid} | Invalid: {n_invalid}"
        ax.text(0.5, -0.08, pct_txt, transform=ax.transAxes, ha="center",
                fontsize=8, color="#374151")

    # Shared legend
    legend_patches = [
        mpatches.Patch(color="#E5E7EB", label="FREE (erased)"),
        mpatches.Patch(color="#2563EB", label="VALID (active data)"),
        mpatches.Patch(color="#DC2626", label="INVALID (stale/garbage)"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=3,
               fontsize=10, frameon=True, edgecolor="#D1D5DB",
               bbox_to_anchor=(0.5, -0.01))

    fig.suptitle("NAND Flash Page State Evolution — Unbuffered Direct Writes\n"
                 "64 Blocks × 64 Pages = 4,096 Physical Pages (16 MiB)",
                 fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()

    path = os.path.join(FIGURES_DIR, "fig7_page_state_evolution.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 8: LBA Access Frequency Heatmap
# ═══════════════════════════════════════════════════════════════════════════════

def fig8_lba_access_heatmap(workload: List[Tuple[int, bytes]]) -> str:
    """Heatmap of per-LBA write frequency revealing hot/cold patterns."""
    # Count access frequency per LBA
    max_lba = max(lba for lba, _ in workload)
    freq = np.zeros(max_lba + 1, dtype=int)
    for lba, _ in workload:
        freq[lba] += 1

    # Reshape into a 2D grid (aim for roughly square)
    n = len(freq)
    # Find factors close to sqrt for nice 2D shape
    cols = int(np.ceil(np.sqrt(n)))
    rows = int(np.ceil(n / cols))
    padded = np.zeros(rows * cols, dtype=int)
    padded[:n] = freq
    grid = padded.reshape(rows, cols)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5),
                                    gridspec_kw={"width_ratios": [2, 1]})

    # Left: heatmap
    im = ax1.imshow(grid, cmap="YlOrRd", aspect="auto",
                    interpolation="nearest")
    ax1.set_title("Per-LBA Write Frequency Heatmap\n"
                  f"{max_lba + 1} LBAs reshaped to {rows}×{cols} grid")
    ax1.set_xlabel(f"LBA Column (0–{cols - 1})")
    ax1.set_ylabel(f"LBA Row (0–{rows - 1})")
    cbar = fig.colorbar(im, ax=ax1, fraction=0.03, pad=0.04)
    cbar.set_label("Write Count", fontweight="bold")

    # Right: histogram of access frequencies
    nonzero_freq = freq[freq > 0]
    ax2.hist(nonzero_freq, bins=30, color="#2563EB", alpha=0.75,
             edgecolor="white", linewidth=0.8)
    ax2.axvline(x=np.mean(nonzero_freq), color="#DC2626", linestyle="--",
                linewidth=2, label=f"Mean: {np.mean(nonzero_freq):.1f}")
    ax2.axvline(x=np.median(nonzero_freq), color="#D97706", linestyle="--",
                linewidth=2, label=f"Median: {np.median(nonzero_freq):.1f}")
    ax2.set_xlabel("Writes per LBA")
    ax2.set_ylabel("Number of LBAs")
    ax2.set_title("Access Frequency Distribution")
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)

    # Stats annotation
    stats_text = (
        f"Total LBAs: {n}\n"
        f"Min writes: {int(freq.min())}\n"
        f"Max writes: {int(freq.max())}\n"
        f"Std dev: {np.std(nonzero_freq):.1f}"
    )
    ax2.text(0.97, 0.97, stats_text, transform=ax2.transAxes, fontsize=8,
             va="top", ha="right", bbox=dict(boxstyle="round,pad=0.4",
             facecolor="#F3F4F6", edgecolor="#D1D5DB"))

    fig.suptitle("LBA Write Access Pattern Analysis — Uniform Random Workload",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()

    path = os.path.join(FIGURES_DIR, "fig8_lba_access_heatmap.png")
    fig.savefig(path)
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all 8 figures and print a summary."""
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("=" * 80)
    print("     PHASE 5: COMPREHENSIVE VISUALIZATIONS & EXTENDED EXPERIMENTS")
    print("=" * 80)

    # Generate shared workload
    print("\n[+] Generating shared 3.2 MB workload (25,000 × 128 B, seed=42)...")
    workload = generate_workload(num_updates=25000, record_size=128,
                                 num_lbas=3200, seed=42)
    print(f"    Workload ready: {len(workload):,} items.")

    generated: List[str] = []

    # Figure 1
    print("\n[1/8] WAF vs. Buffer Size curve (parameter sweep)...")
    t0 = time.perf_counter()
    path = fig1_waf_vs_buffer_size(workload)
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Figure 2
    print("\n[2/8] Cumulative block erasure timeline...")
    t0 = time.perf_counter()
    path = fig2_erasure_timeline(workload)
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Figure 3
    print("\n[3/8] GC overhead breakdown (stacked bar)...")
    t0 = time.perf_counter()
    path = fig3_gc_overhead_breakdown(workload)
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Figure 4
    print("\n[4/8] Working set size sensitivity analysis...")
    t0 = time.perf_counter()
    path = fig4_working_set_sensitivity()
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Figure 5
    print("\n[5/8] Durability vs. WAF Pareto frontier...")
    t0 = time.perf_counter()
    path = fig5_durability_pareto()
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Figure 6
    print("\n[6/8] Power loss data loss distribution (10 seeds × 4 policies)...")
    t0 = time.perf_counter()
    path = fig6_power_loss_boxplot()
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Figure 7
    print("\n[7/8] Page state evolution snapshots (4-panel)...")
    t0 = time.perf_counter()
    path = fig7_page_state_evolution(workload)
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Figure 8
    print("\n[8/8] LBA access frequency heatmap...")
    t0 = time.perf_counter()
    path = fig8_lba_access_heatmap(workload)
    print(f"      ✓ Saved: {path}  ({time.perf_counter() - t0:.1f}s)")
    generated.append(path)

    # Summary
    print("\n" + "=" * 80)
    print("                      ALL 8 FIGURES GENERATED SUCCESSFULLY")
    print("=" * 80)
    for i, p in enumerate(generated, 1):
        print(f"    [{i}] {p}")
    print("=" * 80)


if __name__ == "__main__":
    main()

