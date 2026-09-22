"""Research Visualizations Suite & Extended Parameter Sweeps.

Generates 8 publication-quality figures exploring the design space of the
flash-waf-sim study. All figures are saved to the 'figures/' directory.

Figures:
    1. WAF vs. Buffer Size (log-scale diminishing-returns curve with discrete categorical spacing)
    2. Cumulative Block Erasure Timeline (unbuffered vs. buffered over workload progress)
    3. GC Overhead Breakdown (stacked bar: host writes vs. GC copies by buffer size)
    4. Working Set Size Sensitivity (WAF & erasures vs. num_lbas with log-spaced x-axis)
    5. Durability vs. WAF Pareto Frontier (clean scatter + uncrowded annotations)
    6. Power Loss Data Loss Distribution (box plot with generous margins)
    7. Page State Evolution Snapshots (4-panel grid with clean titles and zero text collisions)
    8. LBA Access Frequency Heatmap (hot/cold write pattern visualization)
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np

from flash_sim import (
    FlashSimulator,
    PageState,
    PowerLossSimulator,
    RingBuffer,
    generate_workload,
)

# Global style configuration
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "figure.facecolor": "white",
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "figures")


def fig1_waf_vs_buffer_size(workload: List[Tuple[int, bytes]]) -> str:
    """Sweep buffer capacity using discrete categorical spacing."""
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

    fig, ax1 = plt.subplots(figsize=(11, 6))

    color_waf = "#1D4ED8"
    color_era = "#DC2626"

    x_indices = np.arange(len(buffer_sizes))
    x_labels = [f"{s} rec\n({s * 128} B)" if s * 128 < 1024 else f"{s} rec\n({s * 128 // 1024} KiB)"
                for s in buffer_sizes]

    ax2 = ax1.twinx()
    ax2.set_ylabel("Block Erasures (P/E Wear Cycles)", color=color_era, fontsize=11, labelpad=10)
    bars = ax2.bar(x_indices, erasures, width=0.45, alpha=0.25, color=color_era,
                   edgecolor=color_era, linewidth=1.2, label="Block Erasures", zorder=2)
    ax2.set_ylim(0, 850)
    ax2.tick_params(axis="y", labelcolor=color_era)

    ax1.set_xlabel("Ring Buffer Capacity", fontsize=11, labelpad=10)
    ax1.set_ylabel("Write Amplification Factor (WAF)", color=color_waf, fontsize=11, labelpad=10)
    line1 = ax1.plot(x_indices, wafs, "o-", color=color_waf, linewidth=2.8,
                     markersize=8, label="WAF", zorder=5)
    ax1.set_yscale("log")
    ax1.set_ylim(0.6, 120)
    ax1.tick_params(axis="y", labelcolor=color_waf)
    ax1.set_xticks(x_indices)
    ax1.set_xticklabels(x_labels, fontsize=9.5)

    for i, (x_pos, waf_val) in enumerate(zip(x_indices, wafs)):
        ax1.annotate(
            f"{waf_val:.1f}×",
            (x_pos, waf_val),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
            fontsize=9,
            color=color_waf,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85),
        )

    ax1.axhline(y=1.0, color="#6B7280", linestyle="--", linewidth=1.2, alpha=0.7, zorder=3)
    ax1.text(0.1, 0.72, "--- WAF = 1.0 (Theoretical Lower Bound)",
             va="center", ha="left", fontsize=9, color="#4B5563", fontstyle="italic")

    lines = line1 + [bars]
    labels = ["WAF (log scale)", "Block Erasures (linear scale)"]
    ax1.legend(lines, labels, loc="upper right", framealpha=0.95, edgecolor="#E5E7EB", fontsize=9.5)

    ax1.set_title("WAF vs. Buffer Size — Diminishing Returns Curve\n"
                  "25,000 Random 128-Byte Updates across 3,200 LBAs",
                  pad=16, fontsize=13, fontweight="bold")
    ax1.grid(axis="y", alpha=0.25, linestyle=":")
    fig.tight_layout()

    path = os.path.join(FIGURES_DIR, "fig1_waf_vs_buffer_size.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig2_erasure_timeline(workload: List[Tuple[int, bytes]]) -> str:
    """Track cumulative erasures over workload progress for unbuffered vs. buffered."""
    sample_interval = 250
    total = len(workload)
    checkpoints = list(range(sample_interval, total + 1, sample_interval))

    sim_unbuf = FlashSimulator(num_blocks=64, pages_per_block=64)
    unbuf_erasures: List[int] = []
    unbuf_gc_copies: List[int] = []
    for i, (lba, data) in enumerate(workload):
        sim_unbuf.write_logical_page(lba=lba, data=data)
        if (i + 1) in checkpoints or (i + 1) == total:
            if (i + 1) % sample_interval == 0 or (i + 1) == total:
                unbuf_erasures.append(sim_unbuf.block_erasures)
                unbuf_gc_copies.append(sim_unbuf.gc_page_copies)

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

    ax1.plot(x, unbuf_erasures, "-", color="#DC2626", linewidth=2.5,
             label=f"Direct Unbuffered (Final: {unbuf_erasures[-1]:,})")
    ax1.plot(x, buf_erasures, "-", color="#059669", linewidth=2.5,
             label=f"Ring-Buffered (Final: {buf_erasures[-1]})")
    ax1.fill_between(x, unbuf_erasures, alpha=0.10, color="#DC2626")
    ax1.fill_between(x, buf_erasures, alpha=0.10, color="#059669")
    ax1.set_xlabel("Host Updates Issued", labelpad=8)
    ax1.set_ylabel("Cumulative Block Erasures", labelpad=8)
    ax1.set_title("Cumulative Block Erasures (P/E Wear)", pad=10)
    ax1.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
    ax1.grid(True, alpha=0.25, linestyle=":")

    ax2.plot(x, unbuf_gc_copies, "-", color="#DC2626", linewidth=2.5,
             label=f"Direct Unbuffered (Final: {unbuf_gc_copies[-1]:,})")
    ax2.plot(x, buf_gc_copies, "-", color="#059669", linewidth=2.5,
             label=f"Ring-Buffered (Final: {buf_gc_copies[-1]})")
    ax2.fill_between(x, unbuf_gc_copies, alpha=0.10, color="#DC2626")
    ax2.fill_between(x, buf_gc_copies, alpha=0.10, color="#059669")
    ax2.set_xlabel("Host Updates Issued", labelpad=8)
    ax2.set_ylabel("Cumulative GC Page Copies", labelpad=8)
    ax2.set_title("Cumulative GC Page Migrations (Overhead)", pad=10)
    ax2.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
    ax2.grid(True, alpha=0.25, linestyle=":")

    fig.suptitle("NAND Flash Wear Accumulation Timeline over Workload Progress",
                 fontsize=14, fontweight="bold", y=0.98)
    fig.subplots_adjust(top=0.86, bottom=0.14, wspace=0.25)

    path = os.path.join(FIGURES_DIR, "fig2_erasure_timeline.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig3_gc_overhead_breakdown(workload: List[Tuple[int, bytes]]) -> str:
    """Stacked bar: host writes vs GC copies for each buffer size with clean labels."""
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
        b_str = f"{cap * 128} B" if cap * 128 < 1024 else f"{cap * 128 // 1024} KiB"
        labels.append(f"{cap} rec\n({b_str})")

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(buffer_sizes))
    width = 0.52

    ax.bar(x, host_writes, width, label="Host Page Writes (Useful Work)",
           color="#2563EB", edgecolor="white", linewidth=1.0)
    ax.bar(x, gc_copies, width, bottom=host_writes,
           label="GC Page Copies (Wasted Overhead)", color="#F59E0B",
           edgecolor="white", linewidth=1.0)

    max_total = max(hw + gc for hw, gc in zip(host_writes, gc_copies))
    ax.set_ylim(0, max_total * 1.15)

    for i, (hw, gc) in enumerate(zip(host_writes, gc_copies)):
        total = hw + gc
        if gc > 0:
            pct = gc / total * 100
            ax.text(i, total + (max_total * 0.02), f"{pct:.0f}% GC\n({total:,})",
                    ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#92400E")
        else:
            ax.text(i, total + (max_total * 0.02), f"0% GC\n({total:,})",
                    ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#059669")

    ax.set_xlabel("Buffer Capacity", fontsize=11, labelpad=8)
    ax.set_ylabel("Total Physical Page Programs", fontsize=11, labelpad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.legend(loc="upper right", framealpha=0.95, fontsize=10)
    ax.set_title("Garbage Collection Overhead Breakdown by Buffer Size\n"
                 "Useful Host Programming vs. Wasted Relocation Writes",
                 pad=14, fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=0.25, linestyle=":")

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, "fig3_gc_overhead_breakdown.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig4_working_set_sensitivity() -> str:
    """Vary num_lbas and measure WAF + erasures using log x-scale."""
    lba_counts = [100, 200, 400, 800, 1600, 3200]
    num_updates = 25000

    unbuf_wafs: List[float] = []
    buf_wafs: List[float] = []
    unbuf_erasures: List[int] = []
    buf_erasures: List[int] = []

    for n_lbas in lba_counts:
        wl = generate_workload(num_updates=num_updates, record_size=128,
                               num_lbas=n_lbas, seed=42)

        sim_u = FlashSimulator(num_blocks=64, pages_per_block=64)
        for lba, data in wl:
            sim_u.write_logical_page(lba=lba, data=data)
        hb = num_updates * 128
        pb = (sim_u.physical_page_writes + sim_u.gc_page_copies) * 4096
        unbuf_wafs.append(pb / hb)
        unbuf_erasures.append(sim_u.block_erasures)

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

    ax1.plot(lba_counts, unbuf_wafs, "o-", color="#DC2626", linewidth=2.5,
             markersize=8, label="Direct Unbuffered")
    ax1.plot(lba_counts, buf_wafs, "s-", color="#059669", linewidth=2.5,
             markersize=8, label="Ring-Buffered (4 KiB)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xticks(lba_counts)
    ax1.set_xticklabels([str(n) for n in lba_counts], fontsize=9)
    ax1.set_ylim(0.6, 150)
    ax1.set_xlabel("Working Set Size (Unique LBAs, log scale)", labelpad=8)
    ax1.set_ylabel("Write Amplification Factor (WAF, log scale)", labelpad=8)
    ax1.set_title("WAF vs. Working Set Size", pad=10)
    ax1.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
    ax1.grid(True, alpha=0.25, linestyle=":")

    for i, n in enumerate(lba_counts):
        util_pct = n / 4096 * 100
        ax1.annotate(
            f"{util_pct:.0f}% util\n({unbuf_wafs[i]:.1f}×)",
            (n, unbuf_wafs[i]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
            fontweight="bold",
            color="#7F1D1D",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85),
        )

    x_indices = np.arange(len(lba_counts))
    bar_width = 0.35
    ax2.bar(x_indices - bar_width / 2, unbuf_erasures, width=bar_width,
            color="#DC2626", label="Direct Unbuffered", alpha=0.85, edgecolor="white")
    ax2.bar(x_indices + bar_width / 2, buf_erasures, width=bar_width,
            color="#059669", label="Ring-Buffered (4 KiB)", alpha=0.85, edgecolor="white")
    ax2.set_xlabel("Working Set Size (Unique LBAs)", labelpad=8)
    ax2.set_ylabel("Total Block Erasures (P/E Wear)", labelpad=8)
    ax2.set_xticks(x_indices)
    ax2.set_xticklabels([str(n) for n in lba_counts], fontsize=9.5)
    ax2.set_ylim(0, 850)
    ax2.set_title("Block Erasures vs. Working Set Size", pad=10)
    ax2.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
    ax2.grid(axis="y", alpha=0.25, linestyle=":")

    for i, val in enumerate(unbuf_erasures):
        ax2.text(i - bar_width / 2, val + 15, f"{val}", ha="center", fontsize=8.5,
                 fontweight="bold", color="#7F1D1D")

    fig.suptitle("Working Set Size Sensitivity Analysis (Capacity Contention)",
                 fontsize=14, fontweight="bold", y=0.98)
    fig.subplots_adjust(top=0.86, bottom=0.14, wspace=0.25)

    path = os.path.join(FIGURES_DIR, "fig4_working_set_sensitivity.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig5_durability_pareto() -> str:
    """Scatter plot of durability rate vs WAF_committed with zero collisions."""
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
        ("Direct Unbuffered (128 B)", 1),
        ("1-Page Buffer (4 KiB)", 32),
        ("2-Page Buffer (8 KiB)", 64),
        ("4-Page Buffer (16 KiB)", 128),
    ]

    sim_power = PowerLossSimulator(num_blocks=64, pages_per_block=64)
    waf_vals: List[float] = []
    dur_vals: List[float] = []
    labels: List[str] = []

    for name, cap in policies:
        res, _ = sim_power.evaluate_policy(
            policy_name=name, capacity_records=cap,
            workload=workload, crash_indices=crash_indices,
        )
        waf_vals.append(res.waf_committed)
        dur_vals.append(res.durability_rate)
        labels.append(name)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    colors = ["#DC2626", "#2563EB", "#7C3AED", "#D97706"]

    ax.fill_between([0, 5], 95, 102, alpha=0.08, color="#059669", zorder=1)
    ax.text(6.0, 99.2, "★ Optimal Sweet Spot\n(WAF ≈ 1.0, Durability > 97%)",
            fontsize=9.5, color="#059669", va="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ECFDF5", edgecolor="#A7F3D0"))

    sorted_pts = sorted(zip(waf_vals, dur_vals), key=lambda p: (p[0], -p[1]))
    ax.plot([p[0] for p in sorted_pts], [p[1] for p in sorted_pts],
            "--", color="#9CA3AF", linewidth=1.5, zorder=2)

    for i, (w, d, lbl, c) in enumerate(zip(waf_vals, dur_vals, labels, colors)):
        ax.scatter(w, d, s=160, c=c, zorder=5, edgecolors="white", linewidth=2)

        if "Direct Unbuffered" in lbl:
            ax.annotate(
                f"{lbl}\nWAF: {w:.1f}× | Durability: {d:.1f}%",
                (w, d),
                textcoords="offset points",
                xytext=(-15, -15),
                ha="right",
                va="top",
                fontsize=9,
                fontweight="bold",
                color=c,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=c, alpha=0.9),
            )
        elif "1-Page" in lbl:
            ax.annotate(
                f"{lbl} [SWEET SPOT]\nWAF: {w:.3f}× | Durability: {d:.1f}%",
                (w, d),
                textcoords="offset points",
                xytext=(18, 5),
                ha="left",
                va="center",
                fontsize=9,
                fontweight="bold",
                color=c,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=c, alpha=0.9),
            )
        elif "2-Page" in lbl:
            ax.annotate(
                f"{lbl}\nWAF: {w:.3f}× | Durability: {d:.1f}%",
                (w, d),
                textcoords="offset points",
                xytext=(18, 0),
                ha="left",
                va="center",
                fontsize=8.5,
                color=c,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=c, alpha=0.9),
            )
        else:
            ax.annotate(
                f"{lbl}\nWAF: {w:.3f}× | Durability: {d:.1f}%",
                (w, d),
                textcoords="offset points",
                xytext=(18, 0),
                ha="left",
                va="center",
                fontsize=8.5,
                color=c,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=c, alpha=0.9),
            )

    ax.set_xlabel("WAF (Committed Bytes) → Lower is Better (Extends Silicon Life)", fontsize=11, labelpad=10)
    ax.set_ylabel("Data Durability Rate (%) → Higher is Better (Less Data Loss)", fontsize=11, labelpad=10)
    ax.set_title("Durability vs. WAF Trade-Off — The Fundamental Pareto Frontier\n"
                 "Evaluated under 50 Randomized Sudden Power Cuts across 25,000 Updates",
                 pad=14, fontsize=13, fontweight="bold")
    ax.set_xlim(-3, 76)
    ax.set_ylim(86, 102.5)
    ax.grid(True, alpha=0.25, linestyle=":")

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, "fig5_durability_pareto.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig6_power_loss_boxplot() -> str:
    """Box plot of per-crash byte loss across 10 random seeds."""
    num_updates = 25000
    num_crashes = 50
    seeds = list(range(42, 52))

    policies = [
        ("Direct Unbuffered (128 B)", 1),
        ("1-Page Buffer (4 KiB)", 32),
        ("2-Page Buffer (8 KiB)", 64),
        ("4-Page Buffer (16 KiB)", 128),
    ]

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
    short_labels = ["Unbuffered\n(128 B)", "1-Page Buffer\n(4 KiB)", "2-Page Buffer\n(8 KiB)", "4-Page Buffer\n(16 KiB)"]
    colors = ["#059669", "#2563EB", "#7C3AED", "#DC2626"]

    ax.set_ylim(-500, 10000)
    ax.axhspan(-400, 100, alpha=0.08, color="#059669", zorder=0)

    bp = ax.boxplot(data_arrays, tick_labels=short_labels, patch_artist=True,
                    widths=0.45, showmeans=True,
                    meanprops=dict(marker="D", markerfacecolor="white",
                                   markeredgecolor="black", markersize=6),
                    medianprops=dict(color="white", linewidth=2.2),
                    flierprops=dict(marker="o", markerfacecolor="#9CA3AF",
                                    markersize=5, alpha=0.7))

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.70)

    rng_jitter = np.random.RandomState(99)
    for i, (arr, c) in enumerate(zip(data_arrays, colors)):
        jitter = rng_jitter.uniform(-0.10, 0.10, size=len(arr))
        ax.scatter([i + 1 + j for j in jitter], arr, s=36, color=c,
                   edgecolors="white", linewidth=1.0, alpha=0.9, zorder=5)

    ax.text(1.0, 700, "Zero Loss\n(100% Durable)", ha="center", va="bottom",
            fontsize=8.5, fontweight="bold", color="#059669")

    for i, arr in enumerate(data_arrays):
        m_val = float(np.mean(arr))
        if m_val > 0:
            ax.text(i + 1, np.max(arr) + 400, f"Mean: {m_val:,.0f} B",
                    ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#374151")

    ax.set_ylabel("Mean Uncommitted Bytes Lost per Crash (Bytes)", fontsize=11, labelpad=8)
    ax.set_xlabel("Buffer Flush Policy", fontsize=11, labelpad=8)
    ax.set_title("Data Loss Distribution Across 10 Independent Workload Seeds\n"
                 "50 Power Loss Events per Seed (Diamonds = Distribution Means)",
                 pad=14, fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=0.25, linestyle=":")

    fig.tight_layout()
    path = os.path.join(FIGURES_DIR, "fig6_power_loss_boxplot.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig7_page_state_evolution(workload: List[Tuple[int, bytes]]) -> str:
    """4-panel snapshots of 64×64 page state grid with zero collisions."""
    total = len(workload)
    checkpoints = [total // 4, total // 2, 3 * total // 4, total]
    step_labels = ["25% Workload", "50% Workload", "75% Workload", "100% Workload"]

    state_map = {PageState.FREE: 0, PageState.VALID: 1, PageState.INVALID: 2}
    cmap = mcolors.ListedColormap(["#F3F4F6", "#2563EB", "#DC2626"])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    snapshots: List[np.ndarray] = []
    stats: List[Tuple[int, int, int]] = []

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

            n_free = int(np.sum(grid == 0))
            n_valid = int(np.sum(grid == 1))
            n_invalid = int(np.sum(grid == 2))
            stats.append((n_free, n_valid, n_invalid))
            cp_idx += 1

    fig, axes = plt.subplots(2, 2, figsize=(13, 11))

    for idx, (ax, grid, label, (nf, nv, ni)) in enumerate(zip(axes.flat, snapshots, step_labels, stats)):
        ax.imshow(grid, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_title(f"{label}\nValid: {nv:,} ({nv/40.96:.0f}%) | Invalid: {ni:,} ({ni/40.96:.0f}%) | Free: {nf}",
                     fontsize=10.5, fontweight="bold", pad=8)
        ax.set_xlabel("Page Index within Block (0–63)", fontsize=9.5, labelpad=6)
        ax.set_ylabel("Block Index (0–63)", fontsize=9.5, labelpad=6)

    legend_patches = [
        mpatches.Patch(color="#F3F4F6", label="FREE (Erased, Ready to Program)"),
        mpatches.Patch(color="#2563EB", label="VALID (Active Live Data)"),
        mpatches.Patch(color="#DC2626", label="INVALID (Stale Garbage — Triggers GC)"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=3,
               fontsize=10, frameon=True, edgecolor="#D1D5DB",
               bbox_to_anchor=(0.5, 0.02))

    fig.suptitle("NAND Flash Physical Page State Evolution — Direct Unbuffered Writes\n"
                 "64 Blocks × 64 Pages = 4,096 Total Physical Silicon Pages (16 MiB)",
                 fontsize=13.5, fontweight="bold", y=0.98)
    fig.subplots_adjust(top=0.90, bottom=0.10, hspace=0.35, wspace=0.25)

    path = os.path.join(FIGURES_DIR, "fig7_page_state_evolution.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig8_lba_access_heatmap(workload: List[Tuple[int, bytes]]) -> str:
    """Heatmap of per-LBA write frequency with uncrowded stats box."""
    max_lba = max(lba for lba, _ in workload)
    freq = np.zeros(max_lba + 1, dtype=int)
    for lba, _ in workload:
        freq[lba] += 1

    n = len(freq)
    cols = int(np.ceil(np.sqrt(n)))
    rows = int(np.ceil(n / cols))
    padded = np.zeros(rows * cols, dtype=int)
    padded[:n] = freq
    grid = padded.reshape(rows, cols)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5),
                                    gridspec_kw={"width_ratios": [1.8, 1.2]})

    im = ax1.imshow(grid, cmap="YlOrRd", aspect="auto", interpolation="nearest")
    ax1.set_title(f"Per-LBA Write Frequency Heatmap ({n:,} Addresses)", pad=10)
    ax1.set_xlabel(f"LBA Column (0–{cols - 1})", labelpad=6)
    ax1.set_ylabel(f"LBA Row (0–{rows - 1})", labelpad=6)
    cbar = fig.colorbar(im, ax=ax1, fraction=0.035, pad=0.04)
    cbar.set_label("Write Count per LBA", fontweight="bold", labelpad=8)

    nonzero_freq = freq[freq > 0]
    ax2.hist(nonzero_freq, bins=25, color="#2563EB", alpha=0.75,
             edgecolor="white", linewidth=0.8)
    ax2.axvline(x=np.mean(nonzero_freq), color="#DC2626", linestyle="--",
                linewidth=2.2, label=f"Mean: {np.mean(nonzero_freq):.1f}")
    ax2.axvline(x=np.median(nonzero_freq), color="#D97706", linestyle="--",
                linewidth=2.2, label=f"Median: {np.median(nonzero_freq):.1f}")
    ax2.set_xlabel("Writes per LBA", labelpad=6)
    ax2.set_ylabel("Number of LBAs", labelpad=6)
    ax2.set_title("Access Frequency Distribution", pad=10)
    ax2.legend(loc="upper right", fontsize=9, framealpha=0.9)
    ax2.grid(axis="y", alpha=0.25, linestyle=":")

    stats_text = (
        f"Total LBAs: {n:,}\n"
        f"Min writes: {int(freq.min())}\n"
        f"Max writes: {int(freq.max())}\n"
        f"Std dev: {np.std(nonzero_freq):.2f}"
    )
    ax2.text(0.04, 0.94, stats_text, transform=ax2.transAxes, fontsize=8.5,
             va="top", ha="left", bbox=dict(boxstyle="round,pad=0.4",
             facecolor="#F3F4F6", edgecolor="#D1D5DB", alpha=0.9))

    fig.suptitle("Synthetic Workload LBA Access Pattern Analysis (Uniform Random Distribution)",
                 fontsize=13.5, fontweight="bold", y=0.98)
    fig.subplots_adjust(top=0.86, bottom=0.14, wspace=0.28)

    path = os.path.join(FIGURES_DIR, "fig8_lba_access_heatmap.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("=" * 80)
    print("            GENERATING EXTENDED RESEARCH VISUALIZATIONS SUITE")
    print("=" * 80)

    workload = generate_workload(num_updates=25000, record_size=128, num_lbas=3200, seed=42)

    generated: List[str] = []
    figures = [
        ("Fig 1: WAF vs. Buffer Size", fig1_waf_vs_buffer_size, [workload]),
        ("Fig 2: Wear Timeline", fig2_erasure_timeline, [workload]),
        ("Fig 3: GC Overhead Breakdown", fig3_gc_overhead_breakdown, [workload]),
        ("Fig 4: Working Set Sensitivity", fig4_working_set_sensitivity, []),
        ("Fig 5: Durability vs. WAF Pareto", fig5_durability_pareto, []),
        ("Fig 6: Power Loss Box Plot", fig6_power_loss_boxplot, []),
        ("Fig 7: Page State Evolution", fig7_page_state_evolution, [workload]),
        ("Fig 8: LBA Access Heatmap", fig8_lba_access_heatmap, [workload]),
    ]

    for name, func, args in figures:
        print(f"[+] Generating {name}...")
        t0 = time.perf_counter()
        path = func(*args)
        print(f"    ✓ Saved: {path} ({time.perf_counter() - t0:.1f}s)")
        generated.append(path)

    print("=" * 80)
    print("                  ALL 8 FIGURES GENERATED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    main()
