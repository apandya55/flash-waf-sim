"""Workload generation utilities for flash memory benchmarking.

Generates reproducible synthetic write workloads simulating small host updates
(e.g., key-value records, database WAL append entries) across configurable
logical address spaces.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


def generate_workload(
    num_updates: int = 25000,
    record_size: int = 128,
    num_lbas: int = 3200,
    seed: int = 42,
) -> List[Tuple[int, bytes]]:
    """Generate a reproducible sequence of random (lba, record_data) updates.
    
    Args:
        num_updates: Total number of update records to generate.
        record_size: Size of each payload in bytes (default: 128 B).
        num_lbas: Size of the active logical address space (unique LBAs).
        seed: Random seed for deterministic reproducibility.
        
    Returns:
        List of (lba, payload_bytes) tuples ready for simulator consumption.
    """
    rng = np.random.RandomState(seed)
    lba_sequence = rng.randint(0, num_lbas, size=num_updates)

    workload: List[Tuple[int, bytes]] = []
    for idx, lba in enumerate(lba_sequence):
        prefix = f"rec_{idx:07d}_lba_{lba:04d}_".encode("ascii")
        padding = b"\xab" * max(0, record_size - len(prefix))
        payload = (prefix + padding)[:record_size]
        workload.append((int(lba), payload))

    return workload
