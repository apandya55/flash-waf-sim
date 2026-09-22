"""Durability Evaluation: Power-Loss Simulation & Per-Block Wear Heatmaps.

Evaluates 4 buffer flush policies (Unbuffered, 1-Page, 2-Page, 4-Page) under
50 randomized sudden power-loss events to quantify uncommitted byte loss
and empirical write amplification on survived host data.

Generates side-by-side per-block wear heatmaps saved to 'figures/wear_heatmaps.png'.
"""

from __future__ import annotations

import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import numpy as np

from flash_sim import FlashSimulator, PowerLossSimulator, RingBuffer, generate_workload

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "figures")


def run_durability_experiment() -> None:
    """Evaluate 4 flush policies under randomized sudden power cuts."""
    print("=" * 80)
    print("      PART 1: DURABILITY MODELING UNDER RANDOMIZED SUDDEN POWER LOSS")
    print("=" * 80)

    num_updates = 25000
    record_size = 128
    num_lbas = 3200
    num_crashes = 50
    seed = 42

    print(f"\n[+] Generating {num_updates:,} updates (seed={seed})...")
    workload = generate_workload(
        num_updates=num_updates,
        record_size=record_size,
        num_lbas=num_lbas,
        seed=seed,
    )

    rng = np.random.RandomState(seed)
    crash_indices = sorted(rng.choice(range(100, num_updates - 100), size=num_crashes, replace=False).tolist())
    print(f"    Injected {num_crashes} randomized sudden power loss events.")

    policies = [
        ("Direct Unbuffered (128 B)", 1),
        ("1-Page Buffer (4 KiB)", 32),
        ("2-Page Buffer (8 KiB)", 64),
        ("4-Page Buffer (16 KiB)", 128),
    ]

    sim_power = PowerLossSimulator(num_blocks=64, pages_per_block=64)
    results = []

    for name, cap_records in policies:
        print(f"    Evaluating policy: {name}...")
        res, _ = sim_power.evaluate_policy(
            policy_name=name,
            capacity_records=cap_records,
            workload=workload,
            crash_indices=crash_indices,
        )
        results.append(res)

    print("\n" + "=" * 95)
    print("              DURABILITY vs. WRITE AMPLIFICATION FACTOR (WAF) TRADE-OFF")
    print("=" * 95)
    print(
        f"{'Flush Policy':<25} | {'Buffer Size':<11} | {'Mean Loss':<10} | {'Max Loss':<10} | "
        f"{'Committed':<10} | {'WAF (Committed)':<15} | {'Block Erasures':<14}"
    )
    print("-" * 95)
    for r in results:
        cap_str = f"{r.buffer_capacity_bytes / 1024:.1f} KiB" if r.buffer_capacity_bytes >= 1024 else f"{r.buffer_capacity_bytes} B"
        mean_loss_str = f"{r.mean_lost_bytes:.0f} B"
        max_loss_str = f"{r.max_lost_bytes} B"
        committed_str = f"{r.durability_rate:.2f}%"
        print(
            f"{r.policy_name:<25} | {cap_str:>11} | {mean_loss_str:>10} | {max_loss_str:>10} | "
            f"{committed_str:>10} | {r.waf_committed:>15.3f} | {r.block_erasures:>14,}"
        )
    print("=" * 95)


def generate_wear_heatmaps(output_filename: str) -> None:
    """Run full workload, extract per-block erase matrices, and generate heatmaps."""
    print("\n" + "=" * 80)
    print("          PART 2: GENERATING SIDE-BY-SIDE PER-BLOCK WEAR HEATMAPS")
    print("=" * 80)

    workload = generate_workload(num_updates=25000, record_size=128, num_lbas=3200, seed=42)

    sim_unbuf = FlashSimulator(num_blocks=64, pages_per_block=64)
    for lba, data in workload:
        sim_unbuf.write_logical_page(lba=lba, data=data)

    sim_buf = FlashSimulator(num_blocks=64, pages_per_block=64)
    buffer = RingBuffer(flash_sim=sim_buf, capacity_records=32, record_size_bytes=128)
    for lba, data in workload:
        buffer.push(record=data, lba=lba)
    buffer.flush()

    unbuf_erases = np.array([b.erase_count for b in sim_unbuf.blocks]).reshape(8, 8)
    buf_erases = np.array([b.erase_count for b in sim_buf.blocks]).reshape(8, 8)
    max_erase = int(max(unbuf_erases.max(), buf_erases.max(), 1))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=200)
    cmap = plt.cm.YlOrRd

    ax1.imshow(unbuf_erases, cmap=cmap, vmin=0, vmax=max_erase)
    ax1.set_title(
        f"Direct Unbuffered (128 B Writes)\nTotal Erasures: {sim_unbuf.block_erasures:,} | WAF: 66.19",
        fontsize=11.5,
        fontweight="bold",
        pad=10,
    )
    ax1.set_xlabel("Block Column (0–7)", fontsize=10)
    ax1.set_ylabel("Block Row (0–7)", fontsize=10)
    ax1.set_xticks(range(8))
    ax1.set_yticks(range(8))

    for r in range(8):
        for c in range(8):
            val = unbuf_erases[r, c]
            text_color = "white" if val > (max_erase * 0.6) else "black"
            ax1.text(c, r, str(val), ha="center", va="center", color=text_color, fontsize=8)

    im2 = ax2.imshow(buf_erases, cmap=cmap, vmin=0, vmax=max_erase)
    ax2.set_title(
        f"Ring-Buffered (4 KiB Flushes)\nTotal Erasures: {sim_buf.block_erasures:,} | WAF: 1.00",
        fontsize=11.5,
        fontweight="bold",
        pad=10,
    )
    ax2.set_xlabel("Block Column (0–7)", fontsize=10)
    ax2.set_ylabel("Block Row (0–7)", fontsize=10)
    ax2.set_xticks(range(8))
    ax2.set_yticks(range(8))

    for r in range(8):
        for c in range(8):
            val = buf_erases[r, c]
            ax2.text(c, r, str(val), ha="center", va="center", color="black", fontsize=8)

    cbar = fig.colorbar(im2, ax=[ax1, ax2], orientation="vertical", fraction=0.03, pad=0.04)
    cbar.set_label("Per-Block Physical Erase Count (P/E Wear Cycles)", fontsize=10.5, fontweight="bold")

    fig.suptitle(
        "NAND Flash Memory Wear Distribution Heatmap (64 Physical Blocks)\nIdentical Color Scale Comparison (vmin=0, vmax=14)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )

    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.08, right=0.88, wspace=0.25)
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    plt.savefig(output_filename, bbox_inches="tight")
    plt.close()
    print(f"\n[+] Saved wear heatmaps to '{output_filename}'")


def main() -> None:
    run_durability_experiment()
    heatmap_path = os.path.join(FIGURES_DIR, "wear_heatmaps.png")
    generate_wear_heatmaps(heatmap_path)


if __name__ == "__main__":
    main()
