"""Durability Modeling and Power-Loss Simulation for Flash Memory.

Investigates the fundamental engineering trade-off:
- Holding writes in volatile RAM reduces Write Amplification and physical block wear.
- However, uncommitted data in RAM is vulnerable to sudden power loss.

This module simulates sudden power-cut events across different flush policies,
measuring uncommitted byte loss, recovery rates, and final write amplification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from flash_sim.buffer import RingBuffer
from flash_sim.simulator import FlashSimulator


@dataclass
class DurabilityResult:
    """Statistics from a simulated power loss run under a specific flush policy.
    
    Attributes:
        policy_name: Descriptive name of the flush policy (e.g., '1-Page Buffer (4 KiB)').
        buffer_capacity_bytes: Maximum size of the volatile buffer in bytes.
        total_updates: Total number of host updates issued.
        total_crashes: Number of sudden power loss events injected.
        total_lost_bytes: Cumulative host bytes lost across all crashes.
        mean_lost_bytes: Average uncommitted bytes lost per crash event.
        max_lost_bytes: Maximum uncommitted bytes lost in any single crash event.
        committed_host_bytes: Total host bytes safely programmed into flash.
        durability_rate: Ratio of host bytes committed vs total host bytes issued (%).
        physical_page_writes: Total page programming operations executed on flash.
        gc_page_copies: Valid pages migrated during Garbage Collection.
        block_erasures: Cumulative block-level erasures.
        waf: Apparent Write Amplification Factor relative to total host bytes issued.
             (Note: Can appear < 1.0 when power cuts wipe uncommitted data from volatile RAM).
        waf_committed: True Write Amplification Factor relative to survived, committed host data
                       (always >= 1.0 in non-compressing FTLs).
    """
    policy_name: str
    buffer_capacity_bytes: int
    total_updates: int
    total_crashes: int
    total_lost_bytes: int
    mean_lost_bytes: float
    max_lost_bytes: int
    committed_host_bytes: int
    durability_rate: float
    physical_page_writes: int
    gc_page_copies: int
    block_erasures: int
    waf: float
    waf_committed: float = 1.0


class PowerLossSimulator:
    """Simulates sudden power-loss events during flash write workloads."""

    def __init__(
        self,
        num_blocks: int = 64,
        pages_per_block: int = 64,
        page_size_bytes: int = 4096,
        record_size_bytes: int = 128,
    ) -> None:
        self.num_blocks = num_blocks
        self.pages_per_block = pages_per_block
        self.page_size_bytes = page_size_bytes
        self.record_size_bytes = record_size_bytes

    def evaluate_policy(
        self,
        policy_name: str,
        capacity_records: int,
        workload: List[Tuple[int, bytes]],
        crash_indices: List[int],
    ) -> Tuple[DurabilityResult, FlashSimulator]:
        """Run a workload with sudden power-loss injections at specified crash indices.
        
        Args:
            policy_name: Name of the policy being evaluated.
            capacity_records: Buffer capacity in records (e.g. 1, 32, 64, 128).
            workload: List of (lba, payload) updates to execute.
            crash_indices: List of update indices at which a sudden power cut occurs.
            
        Returns:
            Tuple of (DurabilityResult, FlashSimulator instance).
        """
        sim = FlashSimulator(
            num_blocks=self.num_blocks,
            pages_per_block=self.pages_per_block,
            page_size_bytes=self.page_size_bytes,
        )
        buffer = RingBuffer(
            flash_sim=sim,
            capacity_records=capacity_records,
            record_size_bytes=self.record_size_bytes,
            page_size_bytes=self.page_size_bytes,
        )

        crash_set = set(crash_indices)
        crashes_encountered = 0
        total_lost_bytes = 0
        max_lost_bytes = 0

        for idx, (lba, data) in enumerate(workload):
            buffer.push(record=data, lba=lba)

            # Check if a sudden power loss occurs at this update
            if idx in crash_set:
                crashes_encountered += 1
                lost = buffer.clear()  # Power loss wipes volatile RAM!
                total_lost_bytes += lost
                if lost > max_lost_bytes:
                    max_lost_bytes = lost

        # Final clean flush of remaining buffer at workload completion
        buffer.flush()

        total_host_bytes = len(workload) * self.record_size_bytes
        committed_host_bytes = total_host_bytes - total_lost_bytes
        durability_rate = (committed_host_bytes / total_host_bytes * 100.0) if total_host_bytes > 0 else 100.0
        mean_lost_bytes = (total_lost_bytes / crashes_encountered) if crashes_encountered > 0 else 0.0

        total_physical_writes = sim.physical_page_writes + sim.gc_page_copies
        total_physical_bytes = total_physical_writes * self.page_size_bytes
        waf = (total_physical_bytes / total_host_bytes) if total_host_bytes > 0 else 1.0
        waf_committed = (total_physical_bytes / committed_host_bytes) if committed_host_bytes > 0 else 1.0

        result = DurabilityResult(
            policy_name=policy_name,
            buffer_capacity_bytes=capacity_records * self.record_size_bytes,
            total_updates=len(workload),
            total_crashes=crashes_encountered,
            total_lost_bytes=total_lost_bytes,
            mean_lost_bytes=mean_lost_bytes,
            max_lost_bytes=max_lost_bytes,
            committed_host_bytes=committed_host_bytes,
            durability_rate=durability_rate,
            physical_page_writes=sim.physical_page_writes,
            gc_page_copies=sim.gc_page_copies,
            block_erasures=sim.block_erasures,
            waf=waf,
            waf_committed=waf_committed,
        )

        return result, sim

