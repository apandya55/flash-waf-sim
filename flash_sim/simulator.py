"""Flash Simulator engine representing the Flash Translation Layer (FTL) and physical NAND storage.

Manages the block hierarchy, Logical-to-Physical (L2P) address mapping,
and physical hardware metrics (writes, garbage collection copies, erasures).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from flash_sim.models import Block, Page, PageState


class FlashSimulator:
    """Simulates a NAND Flash memory storage device and Flash Translation Layer (FTL).
    
    Default configuration models:
    - 64 blocks
    - 64 pages per block (4,096 total physical pages)
    - 4 KiB (4,096 bytes) per page (16 MiB total addressable physical capacity)
    
    Attributes:
        num_blocks: Total number of erase blocks in the flash device.
        pages_per_block: Number of program pages per erase block.
        page_size_bytes: Size of each page in bytes (default 4096 = 4 KiB).
        blocks: List of physical Block objects.
        l2p: Logical-to-Physical translation table mapping host LBA to (block_idx, page_idx).
        physical_page_writes: Count of physical page programming operations requested by host.
        gc_page_copies: Count of valid pages copied between blocks during Garbage Collection.
        block_erasures: Cumulative count of block erase operations executed across all blocks.
    """

    def __init__(
        self,
        num_blocks: int = 64,
        pages_per_block: int = 64,
        page_size_bytes: int = 4096,
    ) -> None:
        self.num_blocks = num_blocks
        self.pages_per_block = pages_per_block
        self.page_size_bytes = page_size_bytes

        # Hardware metrics counters
        self.physical_page_writes: int = 0
        self.gc_page_copies: int = 0
        self.block_erasures: int = 0

        # Logical-to-Physical (L2P) mapping: LBA (int) -> (block_idx, page_idx)
        self.l2p: Dict[int, Tuple[int, int]] = {}

        # Initialize physical blocks and pages
        self.blocks: List[Block] = [
            Block(
                block_id=b,
                pages=[Page(state=PageState.FREE) for _ in range(self.pages_per_block)],
                erase_count=0,
            )
            for b in range(self.num_blocks)
        ]

    @property
    def total_pages(self) -> int:
        """Total physical page count across the entire flash chip."""
        return self.num_blocks * self.pages_per_block

    @property
    def total_capacity_bytes(self) -> int:
        """Total raw physical capacity in bytes."""
        return self.total_pages * self.page_size_bytes

    @property
    def total_free_pages(self) -> int:
        """Total count of pages currently in the FREE state across all blocks."""
        return sum(block.free_page_count for block in self.blocks)

    @property
    def total_valid_pages(self) -> int:
        """Total count of pages currently holding active host data (VALID state)."""
        return sum(block.valid_page_count for block in self.blocks)

    @property
    def total_invalid_pages(self) -> int:
        """Total count of pages holding stale/superseded data (INVALID state)."""
        return sum(block.invalid_page_count for block in self.blocks)

    def get_page(self, block_idx: int, page_idx: int) -> Page:
        """Retrieve a specific physical page by its block and page coordinate.
        
        Args:
            block_idx: Index of the block (0 <= block_idx < num_blocks).
            page_idx: Index of the page within the block (0 <= page_idx < pages_per_block).
            
        Returns:
            The Page instance at the specified coordinate.
            
        Raises:
            IndexError: If block_idx or page_idx is out of range.
        """
        if not (0 <= block_idx < self.num_blocks):
            raise IndexError(
                f"Block index {block_idx} out of range (0 to {self.num_blocks - 1})"
            )
        if not (0 <= page_idx < self.pages_per_block):
            raise IndexError(
                f"Page index {page_idx} out of range (0 to {self.pages_per_block - 1})"
            )
        return self.blocks[block_idx].pages[page_idx]

    def get_physical_address(self, lba: int) -> Optional[Tuple[int, int]]:
        """Look up the physical flash coordinate for a given Logical Block Address (LBA).
        
        Args:
            lba: Host logical block address.
            
        Returns:
            (block_idx, page_idx) tuple if mapped, or None if unmapped.
        """
        return self.l2p.get(lba)

    def __repr__(self) -> str:
        return (
            f"FlashSimulator(blocks={self.num_blocks}, "
            f"pages_per_block={self.pages_per_block}, "
            f"free_pages={self.total_free_pages}/{self.total_pages}, "
            f"writes={self.physical_page_writes}, "
            f"gc_copies={self.gc_page_copies}, "
            f"erasures={self.block_erasures})"
        )

