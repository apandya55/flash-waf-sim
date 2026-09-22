"""WAF Benchmark: Direct Unbuffered vs. Ring-Buffered Execution.

Executes a 3.2 MB synthetic write workload (25,000 updates of 128 bytes each)
against both an unbuffered Flash Translation Layer (FTL) and a Ring-Buffered setup.

Parameters:
- Workload: 3.2 MB (25,000 updates of 128 bytes)
- Working set: 3,200 logical pages (~78% active footprint)
- Geometry: 64 blocks x 64 pages (4,096 total physical pages, 16 MiB raw flash)
- Page size: 4 KiB (4,096 bytes)
- Record size: 128 bytes

Outputs:
- Write Amplification Factor (WAF)
- Physical page programming count
- Garbage collection overhead copies
- Block erasures (P/E silicon wear)
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flash_sim import FlashSimulator, RingBuffer, generate_workload


def run_unbuffered(
    workload: List[Tuple[int, bytes]],
    num_blocks: int = 64,
    pages_per_block: int = 64,
    page_size_bytes: int = 4096,
) -> Dict[str, float]:
    """Execute workload directly against FlashSimulator without buffering."""
    sim = FlashSimulator(
        num_blocks=num_blocks,
        pages_per_block=pages_per_block,
        page_size_bytes=page_size_bytes,
    )

    t0 = time.perf_counter()
    for lba, data in workload:
        sim.write_logical_page(lba=lba, data=data)
    elapsed = time.perf_counter() - t0

    host_bytes = len(workload) * 128
    physical_writes = sim.physical_page_writes + sim.gc_page_copies
    physical_bytes = physical_writes * page_size_bytes

    return {
        "host_bytes": host_bytes,
        "physical_page_writes": sim.physical_page_writes,
        "gc_page_copies": sim.gc_page_copies,
        "total_physical_writes": physical_writes,
        "total_physical_bytes": physical_bytes,
        "block_erasures": sim.block_erasures,
        "waf": physical_bytes / host_bytes,
        "elapsed_seconds": elapsed,
    }


def run_buffered(
    workload: List[Tuple[int, bytes]],
    num_blocks: int = 64,
    pages_per_block: int = 64,
    page_size_bytes: int = 4096,
    capacity_records: int = 32,
) -> Dict[str, float]:
    """Execute workload via RingBuffer (batches 32 records of 128B into 4 KiB pages)."""
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

    t0 = time.perf_counter()
    for lba, data in workload:
        buffer.push(record=data, lba=lba)
    buffer.flush()
    elapsed = time.perf_counter() - t0

    host_bytes = len(workload) * 128
    physical_writes = sim.physical_page_writes + sim.gc_page_copies
    physical_bytes = physical_writes * page_size_bytes

    return {
        "host_bytes": host_bytes,
        "physical_page_writes": sim.physical_page_writes,
        "gc_page_copies": sim.gc_page_copies,
        "total_physical_writes": physical_writes,
        "total_physical_bytes": physical_bytes,
        "block_erasures": sim.block_erasures,
        "waf": physical_bytes / host_bytes,
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    print("=" * 80)
    print("         BENCHMARK: DIRECT UNBUFFERED vs. RING-BUFFERED EXECUTION")
    print("=" * 80)

    num_updates = 25000
    record_size = 128
    num_lbas = 3200
    seed = 42

    total_mb = (num_updates * record_size) / (1024 * 1024)
    print(f"\n[+] Generating {total_mb:.2f} MB workload ({num_updates:,} updates × {record_size} B, seed={seed})...")
    print(f"    Working set: {num_lbas:,} logical pages (78.1% drive utilization)")
    workload = generate_workload(num_updates=num_updates, record_size=record_size, num_lbas=num_lbas, seed=seed)

    print("\n[+] Running Direct Unbuffered (each 128 B write directly to FTL)...")
    res_unbuf = run_unbuffered(workload)
    print(f"    Completed in {res_unbuf['elapsed_seconds']:.2f}s")

    print("\n[+] Running Ring-Buffered (aggregating 32 records into 4 KiB flushes)...")
    res_buf = run_buffered(workload)
    print(f"    Completed in {res_buf['elapsed_seconds']:.2f}s")

    print("\n" + "=" * 80)
    print("                      COMPARATIVE BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Metric':<35} | {'Direct Unbuffered':<18} | {'Ring-Buffered':<18}")
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


if __name__ == "__main__":
    main()
