"""Flash Write Amplification Simulator.

Models the physical characteristics of NAND Flash memory, including:
- Page-level writes (programming) vs Block-level erasures
- Out-of-place updates and Logical-to-Physical (L2P) address translation
- Garbage Collection (GC) and Write Amplification Factor (WAF)
- Volatile buffering (Ring Buffer) and durability trade-offs
"""

from flash_sim.models import PageState, Page, Block
from flash_sim.simulator import FlashSimulator

__all__ = ["PageState", "Page", "Block", "FlashSimulator"]

