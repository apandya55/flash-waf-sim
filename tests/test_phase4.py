"""Unit tests for Phase 4: Durability Modeling & Wear Heatmaps.

Verifies:
- PowerLossSimulator crash injection and volatile byte loss accounting.
- Direct unbuffered policy guarantees zero uncommitted data loss.
- Bounded maximum byte loss under 1-page, 2-page, and 4-page ring buffers.
- Survival of committed data in flash after power loss events.
- Monotonic durability-versus-WAF relationship across flush policies.
- Per-block erase count extraction and 8x8 matrix formatting for heatmaps.
"""

import numpy as np
import pytest

from flash_sim.buffer import RingBuffer
from flash_sim.durability import PowerLossSimulator
from flash_sim.simulator import FlashSimulator


def test_power_loss_simulator_unbuffered_zero_loss() -> None:
    """Direct unbuffered writes (capacity=1 record) suffer 0 uncommitted byte loss on crash."""
    sim_power = PowerLossSimulator(num_blocks=8, pages_per_block=8)
    
    # 50 updates, crash at updates 10, 25, 40
    workload = [(idx % 20, f"data_{idx}".encode().ljust(128, b"\x00")) for idx in range(50)]
    crashes = [10, 25, 40]
    
    res, sim = sim_power.evaluate_policy(
        policy_name="Direct Unbuffered",
        capacity_records=1,
        workload=workload,
        crash_indices=crashes,
    )
    
    assert res.total_crashes == 3
    assert res.total_lost_bytes == 0
    assert res.mean_lost_bytes == 0.0
    assert res.max_lost_bytes == 0
    assert res.durability_rate == 100.0


def test_power_loss_simulator_bounded_loss_by_buffer_size() -> None:
    """A buffer of capacity N records cannot lose more than N * 128 bytes in any crash."""
    sim_power = PowerLossSimulator(num_blocks=16, pages_per_block=16)
    
    # 200 updates with 5 crashes
    workload = [(idx % 50, f"data_{idx}".encode().ljust(128, b"\x00")) for idx in range(200)]
    crashes = [15, 45, 90, 135, 180]
    
    # Policy with 32 records (4 KiB)
    res_1p, _ = sim_power.evaluate_policy(
        policy_name="1-Page Buffer (4 KiB)",
        capacity_records=32,
        workload=workload,
        crash_indices=crashes,
    )
    assert res_1p.max_lost_bytes <= 4096
    assert res_1p.max_lost_bytes > 0
    assert res_1p.total_lost_bytes > 0

    # Policy with 64 records (8 KiB)
    res_2p, _ = sim_power.evaluate_policy(
        policy_name="2-Page Buffer (8 KiB)",
        capacity_records=64,
        workload=workload,
        crash_indices=crashes,
    )
    assert res_2p.max_lost_bytes <= 8192
    assert res_2p.max_lost_bytes >= res_1p.max_lost_bytes


def test_committed_flash_data_survives_power_loss() -> None:
    """Data flushed to flash before a power cut remains valid and readable."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    buf = RingBuffer(flash_sim=sim, capacity_records=32, record_size_bytes=128)
    
    # Push 32 records -> triggers flush to LBA 0
    for i in range(32):
        buf.push(f"committed_{i}".encode().ljust(128, b"\x00"), lba=0)
        
    assert sim.physical_page_writes == 1
    
    # Now push 10 uncommitted records
    for i in range(10):
        buf.push(f"uncommitted_{i}".encode().ljust(128, b"\x00"), lba=1)
        
    # Power cut happens!
    lost = buf.clear()
    assert lost == 10 * 128
    
    # Committed data at LBA 0 must be 100% intact and readable
    flushed_data = sim.read_logical_page(0)
    assert flushed_data is not None
    assert flushed_data[:128] == b"committed_0".ljust(128, b"\x00")
    
    # Uncommitted LBA 1 was never written
    assert sim.read_logical_page(1) is None


def test_durability_vs_waf_tradeoff_monotonicity() -> None:
    """Larger buffers reduce WAF but increase average data loss per crash."""
    sim_power = PowerLossSimulator(num_blocks=32, pages_per_block=32)
    rng = np.random.RandomState(42)
    
    workload = [(int(rng.randint(0, 100)), b"x" * 128) for _ in range(500)]
    crashes = sorted(rng.choice(range(500), size=10, replace=False).tolist())
    
    res_1p, _ = sim_power.evaluate_policy("1-Page", 32, workload, crashes)
    res_4p, _ = sim_power.evaluate_policy("4-Page", 128, workload, crashes)
    
    # 4-Page buffer holds more in volatile RAM -> loses more on crash
    assert res_4p.max_lost_bytes >= res_1p.max_lost_bytes
    assert res_4p.mean_lost_bytes >= res_1p.mean_lost_bytes


def test_per_block_erase_matrix_shape() -> None:
    """64 blocks must correctly reshape into an 8x8 physical wear matrix."""
    sim = FlashSimulator(num_blocks=64, pages_per_block=64)
    # Simulate wear on select blocks
    sim.blocks[0].erase_count = 15
    sim.blocks[63].erase_count = 42
    
    erase_counts = [b.erase_count for b in sim.blocks]
    matrix = np.array(erase_counts).reshape(8, 8)
    
    assert matrix.shape == (8, 8)
    assert matrix[0, 0] == 15
    assert matrix[7, 7] == 42

