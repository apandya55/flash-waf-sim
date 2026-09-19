"""Phase 3 Benchmark: Unbuffered Baseline vs. Ring-Buffered Execution.

This script executes a reproducible benchmark sending 3.2 MB of random updates
to both an unbuffered Flash Translation Layer (FTL) and a Ring-Buffered setup.

Parameters:
- Workload: 3.2 MB (25,000 updates of 128 bytes each)
- Working set: 500 logical pages (2.0 MiB active footprint)
- Random Seed: Fixed NumPy seed (42) for deterministic comparison
- Geometry: 64 blocks x 64 pages (4,096 total physical pages, 16 MiB raw flash)
- Page size: 4 KiB (4,096 bytes)
- Record size: 128 bytes

Calculates:
- Write Amplification Factor (WAF = Physical Bytes Programmed / Host Logical Bytes Written)
- Total block erasures (P/E wear)
- GC overhead copies
"""

from __future__ import annotations

import time
from typing import Dict, List, Tuple

import numpy as np

from flash_sim import FlashSimulator, RingBuffer


def generate_workload(
    num_updates: int = 25000,
    record_size: int = 128,
    num_lbas: int = 500,
    seed: int = 42,
) -> List[Tuple[int, bytes]]:
    """Generate a reproducible sequence of random (lba, record_data) updates."""
    rng = np.random.RandomState(seed)
    lba_sequence = rng.randint(0, num_lbas, size=num_updates)
    
    workload: List[Tuple[int, bytes]] = []
    for idx, lba in enumerate(lba_sequence):
        # Generate identifiable 128-byte payload
        prefix = f"rec_{idx:07d}_lba_{lba:04d}_".encode("ascii")
        padding = b"\xab" * (record_size - len(prefix))
        payload = prefix + padding
        workload.append((int(lba), payload))
        
    return workload


def run_unbuffered_benchmark(
    workload: List[Tuple[int, bytes]],
    num_blocks: int = 64,
    pages_per_block: int = 64,
    page_size_bytes: int = 4096,
) -> Dict[str, float]:
    """Execute workload directly against FlashSimulator (every 128-byte write programs a full page)."""
    sim = FlashSimulator(
        num_blocks=num_blocks,
        pages_per_block=pages_per_block,
        page_size_bytes=page_size_bytes,
    )
    
    start_time = time.perf_counter()
    for lba, data in workload:
        sim.write_logical_page(lba=lba, data=data)
    elapsed = time.perf_counter() - start_time
    
    total_host_bytes = len(workload) * 128
    total_physical_writes = sim.physical_page_writes + sim.gc_page_copies
    total_physical_bytes = total_physical_writes * page_size_bytes
    waf = total_physical_bytes / total_host_bytes
    
    return {
        "host_bytes": total_host_bytes,
        "physical_page_writes": sim.physical_page_writes,
        "gc_page_copies": sim.gc_page_copies,
        "total_physical_writes": total_physical_writes,
        "total_physical_bytes": total_physical_bytes,
        "block_erasures": sim.block_erasures,
        "waf": waf,
        "elapsed_seconds": elapsed,
    }


def run_buffered_benchmark(
    workload: List[Tuple[int, bytes]],
    num_blocks: int = 64,
    pages_per_block: int = 64,
    page_size_bytes: int = 4096,
    capacity_records: int = 32,
) -> Dict[str, float]:
    """Execute workload via RingBuffer (batches 32 records of 128B into single 4 KiB flushes)."""
    sim = FlashSimulator(
        num_blocks=num_blocks,
        pages_per_block=pages_per_block,
        page_size_bytes=page_size_bytes,
    )
    buffer = RingBuffer(
        flash_sim=sim,
        capacity_records=capacity_records,
        record_size_bytes=128,
        page_size_bytes=page_size_bytes,
    )
    
    start_time = time.perf_counter()
    for lba, data in workload:
        buffer.push(record=data, lba=lba)
    buffer.flush()
    elapsed = time.perf_counter() - start_time
    
    total_host_bytes = len(workload) * 128
    total_physical_writes = sim.physical_page_writes + sim.gc_page_copies
    total_physical_bytes = total_physical_writes * page_size_bytes
    waf = total_physical_bytes / total_host_bytes
    
    return {
        "host_bytes": total_host_bytes,
        "physical_page_writes": sim.physical_page_writes,
        "gc_page_copies": sim.gc_page_copies,
        "total_physical_writes": total_physical_writes,
        "total_physical_bytes": total_physical_bytes,
        "block_erasures": sim.block_erasures,
        "waf": waf,
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    print("=" * 80)
    print("   PHASE 3 BENCHMARK: UNBUFFERED BASELINE vs. RING-BUFFERED SIMULATION")
    print("=" * 80)
    
    num_updates = 25000  # 25,000 * 128 bytes = 3,200,000 bytes = 3.2 MB
    record_size = 128
    num_lbas = 3200  # 3,200 active LBAs across 4,096 pages (~78% drive utilization)
    seed = 42
    
    total_mb = (num_updates * record_size) / (1024 * 1024)
    print(f"\n[+] Generating {total_mb:.2f} MB workload ({num_updates:,} updates of {record_size}B, seed={seed})...")
    print(f"    Working set: {num_lbas:,} logical pages (78.1% drive utilization)")
    workload = generate_workload(num_updates=num_updates, record_size=record_size, num_lbas=num_lbas, seed=seed)
    print(f"    Workload generated: {len(workload):,} items ready.")
    
    # 1. Run Unbuffered Baseline
    print("\n[+] Running Unbuffered Baseline (Direct 128B writes to FTL)...")
    res_unbuf = run_unbuffered_benchmark(workload)
    print(f"    Done in {res_unbuf['elapsed_seconds']:.2f}s")
    
    # 2. Run Buffered Setup
    print("\n[+] Running Ring-Buffered Setup (128B records aggregated to 4 KiB pages)...")
    res_buf = run_buffered_benchmark(workload)
    print(f"    Done in {res_buf['elapsed_seconds']:.2f}s")
    
    # 3. Print Results Comparison Table
    print("\n" + "=" * 80)
    print("                      COMPARATIVE BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Metric':<35} | {'Unbuffered Baseline':<18} | {'Ring-Buffered':<18}")
    print("-" * 80)
    print(f"{'Host Data Issued':<35} | {res_unbuf['host_bytes'] / (1024*1024):>15.2f} MB | {res_buf['host_bytes'] / (1024*1024):>15.2f} MB")
    print(f"{'Host Page Writes Issued':<35} | {int(res_unbuf['physical_page_writes']):>18,} | {int(res_buf['physical_page_writes']):>18,}")
    print(f"{'GC Page Copies Triggered':<35} | {int(res_unbuf['gc_page_copies']):>18,} | {int(res_buf['gc_page_copies']):>18,}")
    print(f"{'Total Physical Page Writes':<35} | {int(res_unbuf['total_physical_writes']):>18,} | {int(res_buf['total_physical_writes']):>18,}")
    print(f"{'Total Physical Silicon Bytes':<35} | {res_unbuf['total_physical_bytes'] / (1024*1024):>15.2f} MB | {res_buf['total_physical_bytes'] / (1024*1024):>15.2f} MB")
    print(f"{'Block Erasures (P/E Wear)':<35} | {int(res_unbuf['block_erasures']):>18,} | {int(res_buf['block_erasures']):>18,}")
    print("-" * 80)
    print(f"{'Write Amplification Factor (WAF)':<35} | {res_unbuf['waf']:>18.3f} | {res_buf['waf']:>18.3f}")
    print("=" * 80)
    
    waf_reduction = res_unbuf['waf'] / res_buf['waf']
    erase_reduction = (
        (res_unbuf['block_erasures'] - res_buf['block_erasures']) / res_unbuf['block_erasures'] * 100
        if res_unbuf['block_erasures'] > 0 else 0
    )
    
    print(f"\n[>>>] KEY FINDINGS:")
    print(f"      1. Write Amplification Reduction: {waf_reduction:.1f}x lower WAF ({res_unbuf['waf']:.2f} -> {res_buf['waf']:.2f})")
    print(f"      2. Flash Block Erasure Reduction: {erase_reduction:.1f}% fewer block erasures ({int(res_unbuf['block_erasures'])} -> {int(res_buf['block_erasures'])})")
    print(f"      3. Silicon Endurance Impact: Extends NAND flash lifespan by approximately {waf_reduction:.0f}x!")
    print("=" * 80)


if __name__ == "__main__":
    main()
