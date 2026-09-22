"""Flash Write Amplification Simulator (FlashWAF).

A discrete-event simulation library for NAND Flash Memory, the Flash
Translation Layer (FTL), Write Amplification Factor (WAF) dynamics,
and volatile user-space write buffering.
"""

from flash_sim.buffer import RingBuffer
from flash_sim.durability import DurabilityResult, PowerLossSimulator
from flash_sim.models import Block, FlashOutOfSpaceError, Page, PageState
from flash_sim.simulator import FlashSimulator
from flash_sim.workload import generate_workload

__all__ = [
    "PageState",
    "Page",
    "Block",
    "FlashSimulator",
    "FlashOutOfSpaceError",
    "RingBuffer",
    "PowerLossSimulator",
    "DurabilityResult",
    "generate_workload",
]
