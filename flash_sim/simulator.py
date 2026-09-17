"""Flash Simulator engine representing the Flash Translation Layer (FTL) and physical NAND storage.

Manages the block hierarchy, Logical-to-Physical (L2P) address mapping,
and physical hardware metrics (writes, garbage collection copies, erasures).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flash_sim.models import Block, FlashOutOfSpaceError, Page, PageState


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
        gc_threshold_free_pages: Threshold of free pages that triggers Garbage Collection.
        active_block_idx: Index of current open block receiving sequential page writes.
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
        gc_threshold_free_pages: Optional[int] = None,
    ) -> None:
        self.num_blocks = num_blocks
        self.pages_per_block = pages_per_block
        self.page_size_bytes = page_size_bytes
        self.gc_threshold_free_pages: int = (
            gc_threshold_free_pages if gc_threshold_free_pages is not None else self.pages_per_block
        )

        # Hardware metrics counters
        self.physical_page_writes: int = 0
        self.gc_page_copies: int = 0
        self.block_erasures: int = 0

        # Logical-to-Physical (L2P) mapping: LBA (int) -> (block_idx, page_idx)
        self.l2p: Dict[int, Tuple[int, int]] = {}

        # Active allocation block pointer
        self.active_block_idx: Optional[int] = None

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

    def _allocate_free_page(self, exclude_block_idx: Optional[int] = None) -> Tuple[int, int]:
        """Find and allocate the next free physical page.
        
        Allocates sequentially within the current active block. If the active block
        is full (or excluded), selects a new free block as the active block.
        
        Args:
            exclude_block_idx: Block index to exclude from allocation (used during GC relocation).
            
        Returns:
            (block_idx, page_idx) coordinate of a FREE page.
            
        Raises:
            FlashOutOfSpaceError: If no free pages can be found even after GC.
        """
        # 1. Try to allocate in active block if valid, not excluded, and has space
        if (
            self.active_block_idx is not None
            and self.active_block_idx != exclude_block_idx
            and self.blocks[self.active_block_idx].free_page_count > 0
        ):
            for p_idx, page in enumerate(self.blocks[self.active_block_idx].pages):
                if page.is_free:
                    return (self.active_block_idx, p_idx)

        # 2. Need a new block. First prefer a completely free (clean) block
        candidates = [
            b for b in self.blocks
            if b.block_id != exclude_block_idx and b.free_page_count == self.pages_per_block
        ]

        # If no completely clean block, take any block with free pages
        if not candidates:
            candidates = [
                b for b in self.blocks
                if b.block_id != exclude_block_idx and b.free_page_count > 0
            ]

        if candidates:
            # Pick candidate with the most free pages
            chosen_block = max(candidates, key=lambda b: b.free_page_count)
            if exclude_block_idx is None:
                self.active_block_idx = chosen_block.block_id
            for p_idx, page in enumerate(chosen_block.pages):
                if page.is_free:
                    return (chosen_block.block_id, p_idx)

        # 3. No free pages available among eligible blocks. Try running GC.
        reclaimed_block_id = self.garbage_collect()
        if reclaimed_block_id is not None and reclaimed_block_id != exclude_block_idx:
            if exclude_block_idx is None:
                self.active_block_idx = reclaimed_block_id
            for p_idx, page in enumerate(self.blocks[reclaimed_block_id].pages):
                if page.is_free:
                    return (reclaimed_block_id, p_idx)

        # If still no free pages, search one final time across all eligible blocks
        for b in self.blocks:
            if b.block_id != exclude_block_idx and b.free_page_count > 0:
                if exclude_block_idx is None:
                    self.active_block_idx = b.block_id
                for p_idx, page in enumerate(b.pages):
                    if page.is_free:
                        return (b.block_id, p_idx)

        raise FlashOutOfSpaceError("NAND flash is completely full: no free pages or reclaimable space.")

    def write_logical_page(self, lba: int, data: Any = None) -> Tuple[int, int]:
        """Write a page of data to a host Logical Block Address (LBA).
        
        If the LBA was previously written, its old physical page is marked INVALID
        (out-of-place update). If free pages drop below or equal to gc_threshold_free_pages,
        garbage collection is triggered automatically.
        
        Args:
            lba: Host logical block address.
            data: Payload data to write to the page.
            
        Returns:
            Physical coordinate (block_idx, page_idx) where data was written.
        """
        # 1. If LBA was previously written, mark old physical page as INVALID
        if lba in self.l2p:
            old_b, old_p = self.l2p[lba]
            self.blocks[old_b].pages[old_p].state = PageState.INVALID

        # 2. Check if free pages fell to or below GC threshold
        if self.total_free_pages <= self.gc_threshold_free_pages:
            self.garbage_collect()

        # 3. Allocate a free page
        block_idx, page_idx = self._allocate_free_page()
        target_page = self.blocks[block_idx].pages[page_idx]

        # 4. Program the page
        target_page.state = PageState.VALID
        target_page.lba = lba
        target_page.data = data

        # 5. Update L2P and counters
        self.l2p[lba] = (block_idx, page_idx)
        self.physical_page_writes += 1

        return (block_idx, page_idx)

    def read_logical_page(self, lba: int) -> Optional[Any]:
        """Read the data payload stored at a host Logical Block Address (LBA).
        
        Args:
            lba: Host logical block address.
            
        Returns:
            Data payload if LBA is mapped and valid, otherwise None.
        """
        coord = self.l2p.get(lba)
        if coord is None:
            return None
        block_idx, page_idx = coord
        page = self.blocks[block_idx].pages[page_idx]
        if page.is_valid:
            return page.data
        return None

    def garbage_collect(self) -> Optional[int]:
        """Execute a greedy Garbage Collection cycle.
        
        Selects the victim block with the highest count of INVALID pages,
        copies any remaining VALID pages to free pages in another block,
        erases the victim block, and increments block_erasures.
        
        Returns:
            The block_id of the erased victim block, or None if no blocks have invalid pages.
        """
        # 1. Select candidate victim blocks that contain INVALID pages.
        # Exclude the active write block if other blocks have garbage.
        candidates = [
            b for b in self.blocks
            if b.block_id != self.active_block_idx and b.invalid_page_count > 0
        ]
        if not candidates:
            candidates = [b for b in self.blocks if b.invalid_page_count > 0]

        if not candidates:
            return None

        # Greedy selection: pick block with the highest invalid_page_count.
        # Tie-breaker: prefer block with lower erase_count (wear leveling).
        victim = max(candidates, key=lambda b: (b.invalid_page_count, -b.erase_count))

        # 2. Relocate all VALID pages from victim block
        valid_pages = [
            (p_idx, p) for p_idx, p in enumerate(victim.pages) if p.is_valid
        ]

        for p_idx, page in valid_pages:
            assert page.lba is not None
            # Allocate new free page outside the victim block
            new_b, new_p = self._allocate_free_page(exclude_block_idx=victim.block_id)
            new_page = self.blocks[new_b].pages[new_p]
            new_page.state = PageState.VALID
            new_page.lba = page.lba
            new_page.data = page.data

            # Update L2P mapping to the relocated page
            self.l2p[page.lba] = (new_b, new_p)
            self.gc_page_copies += 1

        # 3. Erase the victim block
        victim_id = victim.block_id
        victim.erase()
        self.block_erasures += 1

        # If the erased block was the active block, reset active block pointer
        if self.active_block_idx == victim_id:
            self.active_block_idx = None

        return victim_id

    def __repr__(self) -> str:
        return (
            f"FlashSimulator(blocks={self.num_blocks}, "
            f"pages_per_block={self.pages_per_block}, "
            f"free_pages={self.total_free_pages}/{self.total_pages}, "
            f"writes={self.physical_page_writes}, "
            f"gc_copies={self.gc_page_copies}, "
            f"erasures={self.block_erasures})"
        )

